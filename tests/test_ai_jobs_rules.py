"""Tests for AIJobsQualityRules, exercised against a small synthetic fixture."""

import pandas as pd
import pytest

from src.quality.ai_jobs_rules import AIJobsQualityRules

COLUMNS = [
    "job_id", "job_title", "job_category", "experience_level", "years_of_experience",
    "education_required", "annual_salary_usd", "salary_min_usd", "salary_max_usd",
    "city", "country", "remote_work", "company_size", "industry", "required_skills",
    "ai_salary_premium_pct", "demand_score", "demand_growth_yoy_pct", "benefits_score_10",
    "posting_year", "posting_month", "is_senior", "is_remote_friendly", "is_llm_role",
    "salary_tier",
]


def _row(**overrides):
    base = {
        "job_id": "AIJOB0001", "job_title": "AI Engineer", "job_category": "AI Engineering",
        "experience_level": "Senior (6-9 yrs)", "years_of_experience": 7,
        "education_required": "Master's", "annual_salary_usd": 200000.0,
        "salary_min_usd": 150000, "salary_max_usd": 250000, "city": "Boston",
        "country": "USA", "remote_work": "On-site", "company_size": "Startup (1-50)",
        "industry": "Finance", "required_skills": "Python|SQL", "ai_salary_premium_pct": 10.0,
        "demand_score": 90, "demand_growth_yoy_pct": 10.0, "benefits_score_10": 7.0,
        "posting_year": 2026, "posting_month": 1, "is_senior": 1, "is_remote_friendly": 0,
        "is_llm_role": 1, "salary_tier": "Senior ($200-300k)",
    }
    base.update(overrides)
    return base


@pytest.fixture
def df():
    return pd.DataFrame([
        _row(job_id="AIJOB0001"),
        _row(job_id="AIJOB0002", annual_salary_usd=400000.0),  # over max but NOT quarantined
        _row(job_id="AIJOB0002", job_title="Duplicate Id"),  # duplicate job_id
        _row(job_id="AIJOB0003", salary_min_usd=300000, salary_max_usd=250000),
        _row(job_id="AIJOB0004", salary_min_usd=0),
        _row(job_id="AIJOB0005", years_of_experience=-1),
        _row(job_id="AIJOB0006", country="Narnia"),
        _row(job_id="AIJOB0007", industry="Wizardry"),
        _row(job_id="AIJOB0008", job_title="Wizard"),
    ], columns=COLUMNS)


def test_annual_salary_over_max_is_not_quarantined(df):
    clean, _ = AIJobsQualityRules().apply(df)
    assert 400000.0 in clean["annual_salary_usd"].values


def test_duplicate_job_id_is_quarantined(df):
    _, quarantine = AIJobsQualityRules().apply(df)
    assert "duplicate_job_id" in quarantine.loc[quarantine["job_title"] == "Duplicate Id", "quarantine_reason"].iloc[0]


def test_salary_min_exceeds_max_is_quarantined(df):
    _, quarantine = AIJobsQualityRules().apply(df)
    assert "salary_min_exceeds_max" in quarantine.loc[quarantine["job_id"] == "AIJOB0003", "quarantine_reason"].iloc[0]


def test_non_positive_salary_min_is_quarantined(df):
    _, quarantine = AIJobsQualityRules().apply(df)
    assert "salary_min_not_positive" in quarantine.loc[quarantine["job_id"] == "AIJOB0004", "quarantine_reason"].iloc[0]


def test_negative_years_of_experience_is_quarantined(df):
    _, quarantine = AIJobsQualityRules().apply(df)
    assert "years_of_experience_negative" in quarantine.loc[quarantine["job_id"] == "AIJOB0005", "quarantine_reason"].iloc[0]


def test_unmapped_country_industry_role_are_quarantined(df):
    _, quarantine = AIJobsQualityRules().apply(df)
    assert "country_not_in_dimension_map" in quarantine.loc[quarantine["job_id"] == "AIJOB0006", "quarantine_reason"].iloc[0]
    assert "industry_not_in_dimension_map" in quarantine.loc[quarantine["job_id"] == "AIJOB0007", "quarantine_reason"].iloc[0]
    assert "job_title_not_in_dimension_map" in quarantine.loc[quarantine["job_id"] == "AIJOB0008", "quarantine_reason"].iloc[0]


def test_clean_and_quarantine_rows_sum_to_input(df):
    clean, quarantine = AIJobsQualityRules().apply(df)
    assert len(clean) + len(quarantine) == len(df)
