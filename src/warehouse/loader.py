"""WarehouseLoader: loads data/processed/*.csv into the Postgres star schema.

Implements the loader contract from the stage-4 schema proposal (section 6):
one transaction, dimensions before facts before the skill bridge before the
mart refresh, `ON CONFLICT DO NOTHING` everywhere so re-running the loader
on the same processed files never duplicates rows. Column lists and natural
keys are never hard-coded here - they come from src.schema.star_schema, so
the DDL, the Python contract and the loader cannot drift from each other
(tests/test_star_schema.py already guards DDL vs star_schema.py; there is
nothing further to check here beyond what SQL itself enforces on insert).

dim_date is not loaded here: schema/001_dimensions.sql pre-seeds it
2020-01-01..2030-12-31, so date_key is always a lookup against an existing
row, never an insert.

Reads from a `processed_dir` (default PROJECT_PATHS.data_processed) rather
than a hard-coded path so tests can point it at a tmp_path of small
synthetic CSVs instead of the real (gitignored, not present in CI)
data/processed/*.csv - same pattern as BaseDataSource(path=...) and
ProjectPaths(root=tmp_path) elsewhere in this project.
"""

import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import psycopg2
import psycopg2.extras

from src.config import PROJECT_PATHS
from src.feature_engineering.survey_feature_engineer import MODEL_VERSION
from src.schema.star_schema import (
    DIM_AI_OPEN_TOPIC,
    DIM_AI_SENTIMENT,
    DIM_COMPANY,
    DIM_COUNTRY,
    DIM_INDUSTRY,
    DIM_ROLE,
    DIM_SKILL,
    FACT_JOB_POSTING,
    FACT_JOB_POSTING_SKILL,
    FACT_LAYOFF_EVENT,
    FACT_SURVEY_RESPONSE,
)

SURVEY_YEAR = 2025  # set explicitly (section 6): the survey has no per-row year of its own.


def connect():
    """Connect using the same POSTGRES_* env vars as setup_database.py."""
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def _date_key(raw: object, fmt: str = "%m/%d/%Y") -> int | None:
    if pd.isna(raw):
        return None
    return int(datetime.strptime(str(raw), fmt).strftime("%Y%m%d"))


def _clean(value):
    """None-ify pandas/NumPy NA so psycopg2 sends SQL NULL, and unwrap
    NumPy scalar types (bool_, int64...) to plain Python ones."""
    if pd.isna(value):
        return None
    return value.item() if hasattr(value, "item") else value


def _insert(cur, table: str, columns: list[str], rows: list[tuple], conflict_key: list[str] | None = None) -> int:
    """INSERT ... ON CONFLICT DO NOTHING. conflict_key=None matches any
    constraint violation (used for dimensions); a natural_key list targets
    that specific UNIQUE constraint (used for facts, per section 6)."""
    if not rows:
        return 0
    cols_sql = ", ".join(columns)
    conflict_sql = f"({', '.join(conflict_key)}) " if conflict_key else ""
    sql = f"INSERT INTO {table} ({cols_sql}) VALUES %s ON CONFLICT {conflict_sql}DO NOTHING RETURNING 1"
    # execute_values pages large row lists into several INSERTs (page_size,
    # default 100); cur.rowcount only reflects the last page, so count via
    # fetch=True instead - it concatenates RETURNING rows across all pages.
    inserted = psycopg2.extras.execute_values(cur, sql, rows, fetch=True)
    return len(inserted)


def _lookup(cur, table: str, key_columns: list[str], surrogate_column: str) -> dict:
    cur.execute(f"SELECT {', '.join(key_columns)}, {surrogate_column} FROM {table}")
    result = {}
    for row in cur.fetchall():
        key = row[:-1]
        result[key[0] if len(key) == 1 else key] = row[-1]
    return result


class WarehouseLoader:
    def __init__(self, conn, processed_dir: Path | None = None):
        self.conn = conn
        self.processed_dir = processed_dir or PROJECT_PATHS.data_processed

    def _read(self, name: str) -> pd.DataFrame:
        return pd.read_csv(self.processed_dir / f"{name}.csv")

    def run(self) -> dict[str, int]:
        """Load everything in one transaction: either it all applies, or
        nothing changes. Returns rows actually inserted per table (0 on a
        repeat run against unchanged input - that is the point)."""
        layoffs = self._read("layoffs")
        ai_jobs = self._read("ai_jobs")
        survey = self._read("survey")
        topics = self._read("survey_topics") if (self.processed_dir / "survey_topics.csv").exists() else pd.DataFrame(
            columns=["model_version", "component_id", "topic_label", "top_terms"]
        )

        counts: dict[str, int] = {}
        with self.conn:
            with self.conn.cursor() as cur:
                counts.update(self._load_dimensions(cur, layoffs, ai_jobs, survey, topics))
                lookups = self._build_lookups(cur)
                counts.update(self._load_facts(cur, layoffs, ai_jobs, survey, lookups))
                counts["fact_job_posting_skill"] = self._load_bridge(cur, ai_jobs)
                self._refresh_mart(cur)
        return counts

    # --- dimensions -----------------------------------------------------

    def _load_dimensions(self, cur, layoffs, ai_jobs, survey, topics) -> dict[str, int]:
        countries = sorted(
            set(layoffs["country_canonical"].dropna())
            | set(ai_jobs["country_canonical"].dropna())
            | set(survey["country_canonical"].dropna())
        )
        n_country = _insert(cur, DIM_COUNTRY.name, ["country_canonical", "continent"], [(c, None) for c in countries])

        industries = sorted(
            set(layoffs["industry_sector"].dropna())
            | set(ai_jobs["industry_sector"].dropna())
            | set(survey["industry_sector"].dropna())
        )
        n_industry = _insert(cur, DIM_INDUSTRY.name, ["industry_sector"], [(i,) for i in industries])

        companies = sorted(set(layoffs["company"].dropna()))
        n_company = _insert(cur, DIM_COMPANY.name, ["company_name"], [(c,) for c in companies])

        role_rows = []
        job_roles = ai_jobs.drop_duplicates("job_title")
        for r in job_roles.itertuples():
            role_rows.append(("job_title", r.job_title, r.role_category, r.job_category, bool(r.is_llm_role)))
        dev_roles = survey.dropna(subset=["DevType"]).drop_duplicates("DevType")
        for r in dev_roles.itertuples():
            role_rows.append(("DevType", r.DevType, r.role_category, None, None))
        n_role = _insert(
            cur, DIM_ROLE.name, ["role_source", "role_title", "role_category", "job_category", "is_llm_role"], role_rows
        )

        sentiment_rows = sorted(set(survey[["AIThreat", "AISelect", "AISent", "AIAcc"]].dropna().itertuples(index=False, name=None)))
        n_sentiment = _insert(cur, DIM_AI_SENTIMENT.name, ["ai_threat", "ai_select", "ai_sent", "ai_acc"], sentiment_rows)

        skills = sorted(
            {s for tags in ai_jobs["required_skills_normalized"].dropna() for s in tags.split("|") if s}
        )
        n_skill = _insert(cur, DIM_SKILL.name, ["skill_name"], [(s,) for s in skills])

        topic_rows = [
            (t.model_version, int(t.component_id), t.topic_label, t.top_terms) for t in topics.itertuples()
        ]
        n_topic = _insert(
            cur, DIM_AI_OPEN_TOPIC.name, ["model_version", "component_id", "topic_label", "top_terms"], topic_rows
        )

        return {
            DIM_COUNTRY.name: n_country,
            DIM_INDUSTRY.name: n_industry,
            DIM_COMPANY.name: n_company,
            DIM_ROLE.name: n_role,
            DIM_AI_SENTIMENT.name: n_sentiment,
            DIM_SKILL.name: n_skill,
            DIM_AI_OPEN_TOPIC.name: n_topic,
        }

    def _build_lookups(self, cur) -> dict[str, dict]:
        return {
            "country": _lookup(cur, DIM_COUNTRY.name, ["country_canonical"], "country_key"),
            "industry": _lookup(cur, DIM_INDUSTRY.name, ["industry_sector"], "industry_key"),
            "company": _lookup(cur, DIM_COMPANY.name, ["company_name"], "company_key"),
            "role": _lookup(cur, DIM_ROLE.name, ["role_source", "role_title"], "role_key"),
            "sentiment": _lookup(cur, DIM_AI_SENTIMENT.name, ["ai_threat", "ai_select", "ai_sent", "ai_acc"], "ai_sentiment_key"),
            "skill": _lookup(cur, DIM_SKILL.name, ["skill_name"], "skill_key"),
            "topic": _lookup(cur, DIM_AI_OPEN_TOPIC.name, ["model_version", "component_id"], "ai_open_topic_key"),
        }

    # --- facts ------------------------------------------------------------

    def _load_facts(self, cur, layoffs, ai_jobs, survey, lookups) -> dict[str, int]:
        layoff_rows = []
        for r in layoffs.itertuples():
            layoff_rows.append((
                _date_key(r.date),
                _date_key(r.date_added),
                lookups["company"].get(r.company),
                lookups["country"].get(r.country_canonical),
                lookups["industry"].get(r.industry_sector),
                r.location,
                r.stage,
                _clean(r.total_laid_off),
                _clean(r.percentage_laid_off),
                _clean(r.funds_raised),
                r.source,
            ))
        n_layoff = _insert(
            cur, FACT_LAYOFF_EVENT.name,
            ["date_key", "date_added_key", "company_key", "country_key", "industry_key", "location", "stage",
             "total_laid_off", "percentage_laid_off", "funds_raised_usd_millions", "source_url"],
            layoff_rows, conflict_key=FACT_LAYOFF_EVENT.natural_key,
        )

        posting_rows = []
        for r in ai_jobs.itertuples():
            posting_rows.append((
                r.job_id,
                r.posting_year * 10000 + r.posting_month * 100 + 1,
                lookups["role"].get(("job_title", r.job_title)),
                lookups["country"].get(r.country_canonical),
                lookups["industry"].get(r.industry_sector),
                r.city,
                r.company_size,
                r.remote_work,
                r.education_required,
                r.experience_level_canonical,
                int(r.years_of_experience),
                float(r.annual_salary_usd),
                float(r.salary_min_usd),
                float(r.salary_max_usd),
                float(r.ai_salary_premium_pct),
                int(r.demand_score),
                float(r.demand_growth_yoy_pct),
                float(r.benefits_score_10),
                bool(r.is_senior),
                bool(r.is_remote_friendly),
                r.salary_tier,
            ))
        n_posting = _insert(
            cur, FACT_JOB_POSTING.name,
            ["job_id", "date_key", "role_key", "country_key", "industry_key", "city", "company_size", "remote_work",
             "education_required", "experience_level_canonical", "years_of_experience", "annual_salary_usd",
             "salary_min_usd", "salary_max_usd", "ai_salary_premium_pct", "demand_score", "demand_growth_yoy_pct",
             "benefits_score_10", "is_senior", "is_remote_friendly", "salary_tier"],
            posting_rows, conflict_key=FACT_JOB_POSTING.natural_key,
        )

        response_rows = []
        for r in survey.itertuples():
            topic_key = None
            if pd.notna(r.ai_open_topic_id):
                topic_key = lookups["topic"].get((MODEL_VERSION, int(r.ai_open_topic_id)))
            response_rows.append((
                SURVEY_YEAR,
                int(r.ResponseId),
                lookups["role"].get(("DevType", r.DevType)) if pd.notna(r.DevType) else None,
                lookups["country"].get(r.country_canonical),
                lookups["industry"].get(r.industry_sector),
                lookups["sentiment"].get((r.AIThreat, r.AISelect, r.AISent, r.AIAcc)),
                r.MainBranch,
                r.Age,
                r.EdLevel,
                r.Employment,
                r.RemoteWork,
                _clean(r.WorkExp),
                _clean(r.YearsCode),
                r.experience_level_canonical if pd.notna(r.experience_level_canonical) else None,
                _clean(r.converted_comp_yearly_winsorized),
                _clean(r.JobSat),
                topic_key,
            ))
        n_response = _insert(
            cur, FACT_SURVEY_RESPONSE.name,
            ["survey_year", "response_id", "role_key", "country_key", "industry_key", "ai_sentiment_key",
             "main_branch", "age_bucket", "ed_level", "employment", "remote_work", "work_exp", "years_code",
             "experience_level_canonical", "converted_comp_yearly_winsorized", "job_sat", "ai_open_topic_key"],
            response_rows, conflict_key=FACT_SURVEY_RESPONSE.natural_key,
        )

        return {
            FACT_LAYOFF_EVENT.name: n_layoff,
            FACT_JOB_POSTING.name: n_posting,
            FACT_SURVEY_RESPONSE.name: n_response,
        }

    def _load_bridge(self, cur, ai_jobs) -> int:
        job_posting_key = _lookup(cur, FACT_JOB_POSTING.name, ["job_id"], "job_posting_key")
        skill_key = _lookup(cur, DIM_SKILL.name, ["skill_name"], "skill_key")

        bridge_rows = []
        for r in ai_jobs.itertuples():
            posting_key = job_posting_key.get(r.job_id)
            if posting_key is None or pd.isna(r.required_skills_normalized):
                continue
            for skill in r.required_skills_normalized.split("|"):
                if skill and skill in skill_key:
                    bridge_rows.append((posting_key, skill_key[skill]))

        return _insert(cur, FACT_JOB_POSTING_SKILL.name, ["job_posting_key", "skill_key"], bridge_rows, conflict_key=FACT_JOB_POSTING_SKILL.natural_key)

    def _refresh_mart(self, cur) -> None:
        cur.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY mart_country_month")


def run_full_load(processed_dir: Path | None = None) -> dict[str, int]:
    """Entry point for callers that just want "load everything, print
    counts" without managing the connection themselves (CLI, Airflow task)."""
    conn = connect()
    try:
        return WarehouseLoader(conn, processed_dir).run()
    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    from dotenv import load_dotenv

    load_dotenv()
    try:
        result = run_full_load()
    except psycopg2.Error as exc:
        print(f"[FAIL] {exc}")
        sys.exit(1)
    for table, n in result.items():
        print(f"[OK]   {table}: {n} row(s) inserted")
