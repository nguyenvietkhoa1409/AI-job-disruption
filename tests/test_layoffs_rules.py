"""Tests for LayoffsQualityRules, exercised against a small synthetic fixture."""

import pandas as pd
import pytest

from src.quality.layoffs_rules import LayoffsQualityRules

COLUMNS = [
    "company", "location", "total_laid_off", "date", "percentage_laid_off",
    "industry", "source", "stage", "funds_raised", "country", "date_added",
]


def _row(**overrides):
    base = {
        "company": "Acme", "location": "Berlin, Non-U.S.", "total_laid_off": 10.0,
        "date": "1/1/2026", "percentage_laid_off": 0.1, "industry": "Finance",
        "source": "https://example.com", "stage": "Series A", "funds_raised": 5.0,
        "country": "Germany", "date_added": "1/2/2026",
    }
    base.update(overrides)
    return base


@pytest.fixture
def df():
    return pd.DataFrame([
        _row(),
        _row(company="Missing Both", total_laid_off=None, percentage_laid_off=None),
        _row(company="Bad Pct", percentage_laid_off=1.5),
        _row(company="Negative Laid Off", total_laid_off=-5.0),
        _row(company="Negative Funds", funds_raised=-1.0),
        _row(company="Bad Country", country="Narnia"),
        _row(company="Bad Industry", industry="Wizardry"),
    ], columns=COLUMNS)


def test_clean_and_missing_magnitude_rows_are_not_quarantined(df):
    clean, quarantine = LayoffsQualityRules().apply(df)
    assert "Acme" in clean["company"].values
    assert "Missing Both" in clean["company"].values


def test_percentage_out_of_range_is_quarantined(df):
    _, quarantine = LayoffsQualityRules().apply(df)
    row = quarantine[quarantine["company"] == "Bad Pct"].iloc[0]
    assert "percentage_laid_off_out_of_range" in row["quarantine_reason"]


def test_negative_counts_are_quarantined(df):
    _, quarantine = LayoffsQualityRules().apply(df)
    assert "total_laid_off_negative" in quarantine.loc[quarantine["company"] == "Negative Laid Off", "quarantine_reason"].iloc[0]
    assert "funds_raised_negative" in quarantine.loc[quarantine["company"] == "Negative Funds", "quarantine_reason"].iloc[0]


def test_unmapped_country_and_industry_are_quarantined(df):
    _, quarantine = LayoffsQualityRules().apply(df)
    assert "country_not_in_dimension_map" in quarantine.loc[quarantine["company"] == "Bad Country", "quarantine_reason"].iloc[0]
    assert "industry_not_in_dimension_map" in quarantine.loc[quarantine["company"] == "Bad Industry", "quarantine_reason"].iloc[0]


def test_clean_and_quarantine_rows_sum_to_input(df):
    clean, quarantine = LayoffsQualityRules().apply(df)
    assert len(clean) + len(quarantine) == len(df)


def test_same_key_conflicting_values_keeps_latest_date_added():
    df = pd.DataFrame([
        _row(company="Dup Co", date_added="1/1/2026", total_laid_off=10.0),
        _row(company="Dup Co", date_added="1/5/2026", total_laid_off=20.0),
    ], columns=COLUMNS)
    clean, quarantine = LayoffsQualityRules().apply(df)
    assert len(clean) == 1
    assert clean.iloc[0]["date_added"] == "1/5/2026"
    assert "duplicate_key_conflicting_values" in quarantine["quarantine_reason"].iloc[0]


def test_exact_duplicate_rows_are_not_double_counted_as_key_conflict():
    df = pd.DataFrame([_row(company="Exact Dup"), _row(company="Exact Dup")], columns=COLUMNS)
    _, quarantine = LayoffsQualityRules().apply(df)
    assert quarantine["quarantine_reason"].tolist() == ["duplicate_row"]
