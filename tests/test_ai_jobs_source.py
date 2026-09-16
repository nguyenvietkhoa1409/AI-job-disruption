"""Tests for AIJobsSource, exercised against a small synthetic fixture CSV
(never the real data/raw/ai_jobs_market_2025_2026.csv - that is covered by validate_sources.py)."""

import pandas as pd
import pytest

from src.data_sources.ai_jobs_source import AIJobsSource

VALID_ROWS = """job_id,job_title,job_category,experience_level,years_of_experience,education_required,annual_salary_usd,salary_min_usd,salary_max_usd,city,country,remote_work,company_size,industry,required_skills,ai_salary_premium_pct,demand_score,demand_growth_yoy_pct,benefits_score_10,posting_year,posting_month,is_senior,is_remote_friendly,is_llm_role,salary_tier
AIJOB0001,AI Agent Developer,AI Engineering,Senior (6-9 yrs),7,Master's,239000.0,155000,290000,Boston,USA,On-site,Startup (1-50),Finance,APIs|Planning Systems|Python|Cloud|SQL|Leadership,13.1,96,16.9,6.8,2026,3,1,0,1,Senior ($200-300k)
AIJOB0002,Prompt Engineer,AI Engineering,Senior (6-9 yrs),2,Bachelor's,,90000,200000,London,UK,Hybrid,Enterprise (5000+),Finance,Python|Documentation|LLM APIs|Prompt Design|NLP|Testing|Cloud,5.4,82,,6.2,2026,1,1,1,1,Upper-Mid ($150-200k)
"""


@pytest.fixture
def fixture_csv(tmp_path):
    path = tmp_path / "ai_jobs_fixture.csv"
    path.write_text(VALID_ROWS)
    return path


def test_load_returns_expected_columns(fixture_csv):
    df = AIJobsSource(path=fixture_csv).load()
    assert list(df.columns) == list(AIJobsSource().describe_columns())
    assert len(df) == 2


def test_load_preserves_missing_values_as_nan(fixture_csv):
    df = AIJobsSource(path=fixture_csv).load()
    assert pd.isna(df.loc[1, "annual_salary_usd"])
    assert pd.isna(df.loc[1, "demand_growth_yoy_pct"])


def test_load_raises_on_missing_column(tmp_path):
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("job_id,job_title\nAIJOB0001,AI Agent Developer\n")
    with pytest.raises(ValueError, match="missing expected columns"):
        AIJobsSource(path=bad_csv).load()


def test_default_path_points_at_data_raw():
    source = AIJobsSource()
    assert source.path.name == "ai_jobs_market_2025_2026.csv"
    assert source.path.parent.name == "raw"
