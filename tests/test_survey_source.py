"""Tests for SurveySource, exercised against a small synthetic fixture CSV
(never the real data/raw/survey_results_public.csv - that is covered by validate_sources.py)."""

import pandas as pd
import pytest

from src.data_sources.survey_source import SurveySource

# Includes extra out-of-scope columns (EmploymentAddl, LearnCode) to prove
# load() scopes the result down to the 18 documented fields.
VALID_ROWS = """ResponseId,MainBranch,Age,EdLevel,Employment,EmploymentAddl,WorkExp,LearnCode,YearsCode,DevType,RemoteWork,Country,Industry,ConvertedCompYearly,AIThreat,AISelect,AISent,AIAcc,JobSat,AIOpen
1,I am a developer by profession,25-34 years old,Bachelor's degree,Employed,Full-time,8.0,Books,14.0,"Developer, back-end",Remote,Ukraine,Fintech,61256.0,I'm not sure,"Yes, I use AI tools daily",Favorable,Somewhat trust,10.0,"Troubleshooting, profiling, debugging"
2,I am a developer by profession,18-24 years old,Master's degree,Employed,Full-time,,Books,,"Developer, front-end",,,,,,,,,
"""


@pytest.fixture
def fixture_csv(tmp_path):
    path = tmp_path / "survey_fixture.csv"
    path.write_text(VALID_ROWS)
    return path


def test_load_returns_expected_columns(fixture_csv):
    df = SurveySource(path=fixture_csv).load()
    assert list(df.columns) == list(SurveySource().describe_columns())
    assert len(df) == 2


def test_load_scopes_out_undocumented_columns(fixture_csv):
    df = SurveySource(path=fixture_csv).load()
    assert "EmploymentAddl" not in df.columns
    assert "LearnCode" not in df.columns


def test_load_preserves_missing_values_as_nan(fixture_csv):
    df = SurveySource(path=fixture_csv).load()
    assert pd.isna(df.loc[1, "WorkExp"])
    assert pd.isna(df.loc[1, "Country"])
    assert pd.isna(df.loc[1, "AIOpen"])


def test_load_raises_on_missing_column(tmp_path):
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("ResponseId,MainBranch\n1,I am a developer by profession\n")
    with pytest.raises(ValueError, match="missing expected columns"):
        SurveySource(path=bad_csv).load()


def test_default_path_points_at_data_raw():
    source = SurveySource()
    assert source.path.name == "survey_results_public.csv"
    assert source.path.parent.name == "raw"
