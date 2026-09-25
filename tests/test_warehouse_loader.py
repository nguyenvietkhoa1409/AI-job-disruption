"""Integration tests for WarehouseLoader against a real Postgres instance.

Needs a reachable Postgres (docker compose up -d, or any host set via the
POSTGRES_* env vars in .env). The db_conn fixture resets the public schema
and rebuilds it from schema/*.sql before every test, so these tests must
never run against a database holding data anyone cares about - same
precondition as setup_database.py --reset.

Skipped automatically (not failed) when no database is reachable, so
`pytest -q` still passes for a contributor who has not run
`docker compose up -d` - same spirit as run_pipeline.py needing data/raw/.

Uses small synthetic processed CSVs (WarehouseLoader(conn, tmp_path)),
not the real (gitignored, not present in CI) data/processed/*.csv - same
pattern as DatasetPipeline's own tests.
"""

from pathlib import Path

import pandas as pd
import psycopg2
import pytest
from dotenv import load_dotenv

from src.feature_engineering.survey_feature_engineer import MODEL_VERSION
from src.warehouse.loader import WarehouseLoader, connect

load_dotenv()

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schema"


@pytest.fixture()
def db_conn():
    try:
        conn = connect()
    except (psycopg2.OperationalError, KeyError):
        pytest.skip("no reachable Postgres (set POSTGRES_* / run docker compose up -d)")
        return
    with conn.cursor() as cur:
        cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        for path in sorted(SCHEMA_DIR.glob("*.sql")):
            cur.execute(path.read_text(encoding="utf-8"))
    conn.commit()
    yield conn
    conn.close()


def _write_processed(processed_dir: Path) -> None:
    processed_dir.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(
        [
            {"company": "Acme", "location": "SF", "date": "1/5/2024", "date_added": "1/6/2024",
             "percentage_laid_off": 0.10, "total_laid_off": 100, "funds_raised": 500.0, "source": "TechCrunch",
             "stage": "Series D", "country_canonical": "United States", "industry_sector": "Technology & Software"},
            {"company": "Acme", "location": "NYC", "date": "3/1/2024", "date_added": "3/2/2024",
             "percentage_laid_off": 0.20, "total_laid_off": 50, "funds_raised": 500.0, "source": "Reuters",
             "stage": "Post-IPO", "country_canonical": "United States", "industry_sector": "Technology & Software"},
            {"company": "Widget Co", "location": "Unknown City", "date": "2/2/2024", "date_added": "2/2/2024",
             "percentage_laid_off": None, "total_laid_off": None, "funds_raised": None, "source": None,
             "stage": "Seed", "country_canonical": None, "industry_sector": None},
        ]
    ).to_csv(processed_dir / "layoffs.csv", index=False)

    pd.DataFrame(
        [
            {"job_id": "AIJOB0001", "job_title": "AI Engineer", "job_category": "Engineering",
             "experience_level_canonical": "Mid", "years_of_experience": 4, "education_required": "Bachelor's",
             "annual_salary_usd": 150000.0, "salary_min_usd": 140000, "salary_max_usd": 160000, "city": "SF",
             "country_canonical": "United States", "remote_work": "Hybrid", "company_size": "Large",
             "industry_sector": "Technology & Software", "required_skills_normalized": "Python|Cloud",
             "ai_salary_premium_pct": 15.0, "demand_score": 80, "demand_growth_yoy_pct": 10.0,
             "benefits_score_10": 8.5, "posting_year": 2024, "posting_month": 3, "is_senior": 0,
             "is_remote_friendly": 1, "is_llm_role": 1, "salary_tier": "Mid ($100-150k)", "role_category": "Emerging"},
            {"job_id": "AIJOB0002", "job_title": "AI Engineer", "job_category": "Engineering",
             "experience_level_canonical": "Lead", "years_of_experience": 12, "education_required": "Master's",
             "annual_salary_usd": 220000.0, "salary_min_usd": 200000, "salary_max_usd": 240000, "city": "NYC",
             "country_canonical": "United States", "remote_work": "On-site", "company_size": "Large",
             "industry_sector": "Technology & Software", "required_skills_normalized": "Python|SQL",
             "ai_salary_premium_pct": 20.0, "demand_score": 90, "demand_growth_yoy_pct": 12.0,
             "benefits_score_10": 9.0, "posting_year": 2024, "posting_month": 4, "is_senior": 1,
             "is_remote_friendly": 0, "is_llm_role": 1, "salary_tier": "Senior ($200-300k)", "role_category": "Emerging"},
        ]
    ).to_csv(processed_dir / "ai_jobs.csv", index=False)

    pd.DataFrame(
        [
            {"ResponseId": 1, "MainBranch": "I am a developer", "Age": "25-34", "EdLevel": "Bachelor's",
             "Employment": "Employed", "RemoteWork": "Remote", "WorkExp": 4.0, "YearsCode": 6.0,
             "DevType": "Developer, back-end", "role_category": "Traditional", "country_canonical": "United States",
             "industry_sector": "Technology & Software", "AIThreat": "No", "AISelect": "Yes", "AISent": "Favorable",
             "AIAcc": "High", "JobSat": 8.0, "experience_level_canonical": "Mid",
             "converted_comp_yearly_winsorized": 120000.0, "ai_open_topic_id": 0.0},
            {"ResponseId": 2, "MainBranch": "I am a developer", "Age": "Prefer not to say", "EdLevel": "Master's",
             "Employment": "Employed", "RemoteWork": "On-site", "WorkExp": None, "YearsCode": None,
             "DevType": None, "role_category": None, "country_canonical": None, "industry_sector": None,
             "AIThreat": "No", "AISelect": "Yes", "AISent": "Favorable", "AIAcc": "High", "JobSat": None,
             "experience_level_canonical": None, "converted_comp_yearly_winsorized": None, "ai_open_topic_id": None},
        ]
    ).to_csv(processed_dir / "survey.csv", index=False)

    pd.DataFrame(
        [{"model_version": MODEL_VERSION, "component_id": 0, "topic_label": "AI capability skepticism",
          "top_terms": "ai, tools"}]
    ).to_csv(processed_dir / "survey_topics.csv", index=False)


@pytest.fixture()
def processed_dir(tmp_path):
    _write_processed(tmp_path)
    return tmp_path


def _table_count(conn, table: str) -> int:
    with conn.cursor() as cur:
        cur.execute(f"SELECT count(*) FROM {table}")
        return cur.fetchone()[0]


def test_run_loads_every_table(db_conn, processed_dir):
    counts = WarehouseLoader(db_conn, processed_dir).run()

    assert counts["dim_country"] == 1  # only "United States" (Widget Co / response 2 have no country)
    assert counts["dim_industry"] == 1
    assert counts["dim_company"] == 2  # Acme, Widget Co
    assert counts["dim_role"] == 2  # AI Engineer (job_title), Developer back-end (DevType)
    assert counts["dim_ai_sentiment"] == 1  # both survey rows share the same 4 answers
    assert counts["dim_skill"] == 3  # Python, Cloud, SQL
    assert counts["dim_ai_open_topic"] == 1
    assert counts["fact_layoff_event"] == 3
    assert counts["fact_job_posting"] == 2
    assert counts["fact_survey_response"] == 2
    assert counts["fact_job_posting_skill"] == 4  # 2 skills x 2 postings

    assert _table_count(db_conn, "fact_layoff_event") == 3
    assert _table_count(db_conn, "fact_job_posting_skill") == 4


def test_run_twice_is_idempotent(db_conn, processed_dir):
    WarehouseLoader(db_conn, processed_dir).run()
    before = {t: _table_count(db_conn, t) for t in ["dim_company", "dim_role", "fact_layoff_event", "fact_job_posting", "fact_survey_response", "fact_job_posting_skill"]}

    second_counts = WarehouseLoader(db_conn, processed_dir).run()

    assert all(n == 0 for n in second_counts.values()), second_counts
    after = {t: _table_count(db_conn, t) for t in before}
    assert before == after


def test_same_company_keeps_different_stage_per_event(db_conn, processed_dir):
    WarehouseLoader(db_conn, processed_dir).run()

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT f.stage, f.company_key FROM fact_layoff_event f "
            "JOIN dim_company c ON c.company_key = f.company_key WHERE c.company_name = 'Acme'"
        )
        rows = cur.fetchall()

    assert {r[0] for r in rows} == {"Series D", "Post-IPO"}
    assert len({r[1] for r in rows}) == 1  # same company_key both times - stage varies, company identity does not


def test_missing_country_and_industry_load_as_null_fk(db_conn, processed_dir):
    WarehouseLoader(db_conn, processed_dir).run()

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT country_key, industry_key FROM fact_layoff_event WHERE location = 'Unknown City'"
        )
        country_key, industry_key = cur.fetchone()

    assert country_key is None
    assert industry_key is None


def test_mart_refresh_buckets_missing_country_as_unknown(db_conn, processed_dir):
    WarehouseLoader(db_conn, processed_dir).run()

    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT layoff_events FROM mart_country_month WHERE country_canonical = '(Unknown)' AND year = 2024 AND month = 2"
        )
        row = cur.fetchone()

    assert row is not None
    assert row[0] == 1
