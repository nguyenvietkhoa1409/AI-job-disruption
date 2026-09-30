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
             "Employment": "Employed", "RemoteWork": None, "WorkExp": None, "YearsCode": None,
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


def _query(conn, sql: str, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def _append_layoffs(processed_dir: Path, rows: list[dict]) -> None:
    path = processed_dir / "layoffs.csv"
    pd.concat([pd.read_csv(path), pd.DataFrame(rows)], ignore_index=True).to_csv(path, index=False)


_FINANCE_LAYOFF = {
    "company": "Bank Co", "location": "NYC", "date": "3/10/2024", "date_added": "3/11/2024",
    "percentage_laid_off": 0.05, "total_laid_off": 10, "funds_raised": 1.0, "source": "z",
    "stage": "Post-IPO", "country_canonical": "United States", "industry_sector": "Finance",
}


def test_mart_buckets_missing_country_and_industry_as_unknown(db_conn, processed_dir):
    WarehouseLoader(db_conn, processed_dir).run()

    rows = _query(
        db_conn,
        "SELECT layoff_events, total_laid_off_sum, events_with_headcount, pct_laid_off_nonnull_count "
        "FROM mart_country_industry_month WHERE country_canonical = '(Unknown)' "
        "AND industry_sector = '(Unknown)' AND month_start = DATE '2024-02-01'",
    )

    # Widget Co: one event, but neither headcount nor percentage was disclosed.
    assert rows == [(1, 0, 0, 0)]


def test_mart_stores_additive_sums_and_counts_not_averages(db_conn, processed_dir):
    # Acme SF (Jan, pct 0.10) plus a Jan shutdown with no headcount and a Jan event at pct 0.30.
    _append_layoffs(processed_dir, [
        {"company": "Acme", "location": "Austin", "date": "1/20/2024", "date_added": "1/21/2024",
         "percentage_laid_off": 1.0, "total_laid_off": None, "funds_raised": 500.0, "source": "x",
         "stage": "Series D", "country_canonical": "United States", "industry_sector": "Technology & Software"},
        {"company": "Acme", "location": "Denver", "date": "1/25/2024", "date_added": "1/26/2024",
         "percentage_laid_off": 0.30, "total_laid_off": 20, "funds_raised": 500.0, "source": "y",
         "stage": "Series D", "country_canonical": "United States", "industry_sector": "Technology & Software"},
    ])
    WarehouseLoader(db_conn, processed_dir).run()

    (row,) = _query(
        db_conn,
        "SELECT layoff_events, total_laid_off_sum, events_with_headcount, pct_laid_off_sum, "
        "pct_laid_off_nonnull_count, shutdown_events FROM mart_country_industry_month "
        "WHERE country_canonical = 'United States' AND stage = 'Series D' AND month_start = DATE '2024-01-01'",
    )

    events, headcount, with_headcount, pct_sum, pct_n, shutdowns = row
    assert (events, headcount, with_headcount, pct_n, shutdowns) == (3, 120, 2, 3, 1)
    assert float(pct_sum) == pytest.approx(1.40)  # 0.10 + 1.0 + 0.30: exact, unlike an average of averages


def test_comparison_window_follows_ai_jobs_posting_dates(db_conn, processed_dir):
    WarehouseLoader(db_conn, processed_dir).run()

    # Postings are 2024-03 and 2024-04 in the fixture.
    assert _query(db_conn, "SELECT start_date, end_date FROM vw_comparison_window") == [
        (pd.Timestamp("2024-03-01").date(), pd.Timestamp("2024-04-30").date())
    ]


def test_industry_overview_uses_window_and_keeps_no_data_as_null(db_conn, processed_dir):
    _append_layoffs(processed_dir, [_FINANCE_LAYOFF])
    WarehouseLoader(db_conn, processed_dir).run()

    rows = {r[0]: r[1:] for r in _query(
        db_conn,
        "SELECT industry_sector, layoff_events, total_laid_off, job_postings, survey_responses, "
        "ai_threat_answered_n, ai_threat_yes_n FROM mart_industry_overview",
    )}

    # Technology: only Acme NYC (3/1) is inside the Mar-Apr window; Acme SF (Jan) is not.
    assert rows["Technology & Software"] == (1, 50, 2, 1, 1, 0)
    # Finance: a layoff in the window but no AI postings and no survey rows -> NULL, not 0.
    assert rows["Finance"] == (1, 10, None, None, None, None)


def test_overview_marts_keep_undisclosed_headcount_as_null_not_zero(db_conn, processed_dir):
    _append_layoffs(processed_dir, [
        {"company": "Edu Co", "location": "Boston", "date": "3/12/2024", "date_added": "3/13/2024",
         "percentage_laid_off": 0.5, "total_laid_off": None, "funds_raised": 1.0, "source": "e",
         "stage": "Seed", "country_canonical": "Canada", "industry_sector": "Education"},
    ])
    WarehouseLoader(db_conn, processed_dir).run()

    # One event in the window, but nobody disclosed a headcount: "no data", not "0 laid off".
    assert _query(
        db_conn,
        "SELECT layoff_events, total_laid_off, events_with_headcount FROM mart_industry_overview "
        "WHERE industry_sector = 'Education'",
    ) == [(1, None, 0)]


def test_country_overview_is_restricted_to_ai_jobs_countries_with_continent(db_conn, processed_dir):
    WarehouseLoader(db_conn, processed_dir).run()

    rows = _query(
        db_conn,
        "SELECT country_canonical, continent, job_postings, median_salary_usd, layoff_events "
        "FROM mart_country_overview",
    )

    assert [(r[0], r[2], float(r[3]), r[4]) for r in rows] == [("United States", 2, 185000.0, 1)]
    assert rows[0][1] is not None  # continent is filled, not NULL


def test_share_gap_only_covers_sectors_present_in_both_sources(db_conn, processed_dir):
    _append_layoffs(processed_dir, [_FINANCE_LAYOFF])
    WarehouseLoader(db_conn, processed_dir).run()

    rows = _query(
        db_conn,
        "SELECT industry_sector, layoff_share, posting_share, share_gap_pp FROM mart_sector_share_gap",
    )

    # Finance has layoffs but no AI postings, so it is excluded; Technology is
    # the only shared sector, so both shares renormalise to 1 and the gap is 0.
    assert [(r[0], float(r[1]), float(r[2]), float(r[3])) for r in rows] == [
        ("Technology & Software", 1.0, 1.0, 0.0)
    ]


def test_country_continent_is_backfilled_when_previously_null(db_conn, processed_dir):
    WarehouseLoader(db_conn, processed_dir).run()
    with db_conn.cursor() as cur:
        cur.execute("UPDATE dim_country SET continent = NULL")  # state of a database loaded before the fix
    db_conn.commit()

    WarehouseLoader(db_conn, processed_dir).run()

    assert _query(db_conn, "SELECT count(*) FROM dim_country WHERE continent IS NULL") == [(0,)]


def test_layoff_event_view_orders_stages_and_flags_shutdowns(db_conn, processed_dir):
    WarehouseLoader(db_conn, processed_dir).run()

    rows = {r[0]: r[1:] for r in _query(
        db_conn, "SELECT stage, stage_order, is_shutdown FROM vw_layoff_event"
    )}

    assert rows["Seed"][0] < rows["Series D"][0] < rows["Post-IPO"][0]
    assert rows["Series D"][1] is False
    assert rows["Seed"][1] is None  # Widget Co disclosed no percentage: unknown, not False


def test_sentiment_profile_derives_scores_and_topic_kind(db_conn, processed_dir):
    WarehouseLoader(db_conn, processed_dir).run()

    rows = _query(
        db_conn,
        "SELECT ai_threat_yes, ai_sent_score, ai_acc_score, ai_adopter, topic_label, topic_kind "
        "FROM vw_sentiment_profile WHERE survey_year = 2025 ORDER BY response_key",
    )

    # Response 1: AIThreat 'No', 'Favorable' -> 4, the fixture's 'High' trust is not a real
    # survey answer -> NULL score, AISelect 'Yes' is not a frequency answer ('Yes, ...')
    # -> not an adopter, and topic 0 is a stance topic.
    assert rows[0] == (False, 4, None, False, "AI capability skepticism", "stance")
    assert rows[1][4:] == (None, None)  # no topic for the second respondent


def test_role_salary_view_keeps_datasets_separate(db_conn, processed_dir):
    WarehouseLoader(db_conn, processed_dir).run()

    rows = _query(db_conn, "SELECT dataset, count(*) FROM vw_role_salary GROUP BY dataset ORDER BY dataset")

    # 2 AI Jobs postings; 1 survey respondent with compensation (response 2 has none).
    assert rows == [("AI Jobs", 2), ("Survey", 1)]


def test_skill_views(db_conn, processed_dir):
    WarehouseLoader(db_conn, processed_dir).run()

    leaderboard = {r[0]: r[1] for r in _query(db_conn, "SELECT skill_name, postings FROM vw_skill_leaderboard")}
    assert leaderboard == {"Python": 2, "Cloud": 1, "SQL": 1}

    share = {r[0]: float(r[1]) for r in _query(db_conn, "SELECT skill_name, pct_of_category FROM vw_skill_category")}
    assert share == {"Python": 1.0, "Cloud": 0.5, "SQL": 0.5}


def test_topic_cross_view_counts_respondents_with_a_topic(db_conn, processed_dir):
    WarehouseLoader(db_conn, processed_dir).run()

    assert _query(db_conn, "SELECT topic_label, role_category, ai_threat, responses FROM vw_topic_cross") == [
        ("AI capability skepticism", "Traditional", "No", 1)
    ]


def test_run_log_records_each_source_and_appends_on_rerun(db_conn, processed_dir, tmp_path):
    quarantine_dir = tmp_path / "quarantine"
    quarantine_dir.mkdir()
    pd.DataFrame({"company": ["Bad Co", "Worse Co"], "quarantine_reason": ["r1", "r2"]}).to_csv(
        quarantine_dir / "layoffs.csv", index=False
    )

    WarehouseLoader(db_conn, processed_dir, quarantine_dir).run()
    first = _query(
        db_conn,
        "SELECT source, rows_clean, rows_quarantined, rows_inserted FROM pipeline_run_log ORDER BY source",
    )
    assert first == [("ai_jobs", 2, 0, 2), ("layoffs", 3, 2, 3), ("survey", 2, 0, 2)]

    WarehouseLoader(db_conn, processed_dir, quarantine_dir).run()
    second = _query(
        db_conn,
        "SELECT source, rows_inserted FROM pipeline_run_log ORDER BY run_log_key DESC LIMIT 3",
    )
    assert _table_count(db_conn, "pipeline_run_log") == 6  # append-only history
    assert {(s, n) for s, n in second} == {("layoffs", 0), ("ai_jobs", 0), ("survey", 0)}


def test_missing_text_values_load_as_null_not_nan_string(db_conn, processed_dir):
    # Regression: pandas stores a missing text cell as float NaN; without
    # cleaning, Postgres stores it as the literal string "NaN".
    WarehouseLoader(db_conn, processed_dir).run()

    with db_conn.cursor() as cur:
        cur.execute("SELECT source_url FROM fact_layoff_event WHERE location = 'Unknown City'")
        assert cur.fetchone()[0] is None
        cur.execute("SELECT remote_work FROM fact_survey_response WHERE response_id = 2")
        assert cur.fetchone()[0] is None
        cur.execute(
            "SELECT count(*) FROM fact_survey_response WHERE 'NaN' IN "
            "(main_branch, age_bucket, ed_level, employment, remote_work, experience_level_canonical)"
        )
        assert cur.fetchone()[0] == 0
