"""Tests for SurveyQualityRules, exercised against a small synthetic fixture."""

import pandas as pd
import pytest

from src.quality.survey_rules import SurveyQualityRules

COLUMNS = [
    "ResponseId", "MainBranch", "Age", "EdLevel", "Employment", "WorkExp", "YearsCode",
    "DevType", "RemoteWork", "Country", "Industry", "ConvertedCompYearly", "AIThreat",
    "AISelect", "AISent", "AIAcc", "JobSat", "AIOpen",
]


def _row(**overrides):
    base = {
        "ResponseId": 1, "MainBranch": "I am a developer by profession",
        "Age": "25-34 years old", "EdLevel": "Bachelor's degree", "Employment": "Employed",
        "WorkExp": 8.0, "YearsCode": 14.0, "DevType": "Developer, back-end",
        "RemoteWork": "Remote", "Country": "Germany", "Industry": "Finance",
        "ConvertedCompYearly": 90000.0, "AIThreat": "I'm not sure",
        "AISelect": "Yes", "AISent": "Favorable", "AIAcc": "Somewhat trust", "JobSat": 8.0,
        "AIOpen": "Debugging",
    }
    base.update(overrides)
    return base


@pytest.fixture
def df():
    return pd.DataFrame([
        _row(ResponseId=1),
        # Career-changer: WorkExp > YearsCode, NOT quarantined (legitimate)
        _row(ResponseId=2, WorkExp=20.0, YearsCode=3.0, MainBranch="I am not primarily a developer, but I write code sometimes as part of my work/studies"),
        _row(ResponseId=3, Age="18-24 years old", WorkExp=50.0),  # implausible for age
        _row(ResponseId=4, Age="18-24 years old", YearsCode=30.0),  # implausible for age
        _row(ResponseId=5, Age="Prefer not to say", WorkExp=90.0),  # unresolvable age, not quarantined
        _row(ResponseId=6, Country="Narnia"),
        _row(ResponseId=7, Industry="Wizardry"),
        _row(ResponseId=8, DevType="Wizard"),
    ], columns=COLUMNS)


def test_career_changer_work_exp_over_years_code_is_not_quarantined(df):
    clean, _ = SurveyQualityRules().apply(df)
    assert 2 in clean["ResponseId"].values


def test_unresolvable_age_bucket_is_not_quarantined(df):
    clean, _ = SurveyQualityRules().apply(df)
    assert 5 in clean["ResponseId"].values


def test_work_exp_and_years_code_implausible_for_age_are_quarantined(df):
    _, quarantine = SurveyQualityRules().apply(df)
    assert "work_exp_implausible_for_age" in quarantine.loc[quarantine["ResponseId"] == 3, "quarantine_reason"].iloc[0]
    assert "years_code_implausible_for_age" in quarantine.loc[quarantine["ResponseId"] == 4, "quarantine_reason"].iloc[0]


def test_unmapped_country_industry_devtype_are_quarantined(df):
    _, quarantine = SurveyQualityRules().apply(df)
    assert "country_not_in_dimension_map" in quarantine.loc[quarantine["ResponseId"] == 6, "quarantine_reason"].iloc[0]
    assert "industry_not_in_dimension_map" in quarantine.loc[quarantine["ResponseId"] == 7, "quarantine_reason"].iloc[0]
    assert "devtype_not_in_dimension_map" in quarantine.loc[quarantine["ResponseId"] == 8, "quarantine_reason"].iloc[0]


def test_duplicate_response_id_is_quarantined():
    df = pd.DataFrame([_row(ResponseId=1), _row(ResponseId=1)], columns=COLUMNS)
    clean, quarantine = SurveyQualityRules().apply(df)
    assert len(clean) == 1
    assert "duplicate_response_id" in quarantine["quarantine_reason"].iloc[0]


def test_clean_and_quarantine_rows_sum_to_input(df):
    clean, quarantine = SurveyQualityRules().apply(df)
    assert len(clean) + len(quarantine) == len(df)
