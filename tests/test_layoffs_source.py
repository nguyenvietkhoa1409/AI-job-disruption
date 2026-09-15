"""Tests for LayoffsSource, exercised against a small synthetic fixture CSV
(never the real data/raw/layoffs.csv - that is covered by validate_sources.py)."""

import pandas as pd
import pytest

from src.data_sources.layoffs_source import LayoffsSource

VALID_ROWS = """company,location,total_laid_off,date,percentage_laid_off,industry,source,stage,funds_raised,country,date_added
Neo Financial,"Calgary, Non-U.S.",102.0,9/8/2026,0.1,Finance,https://example.com/a,Series D,544,Canada,9/9/2026
Samsung,"Gurugram, Non-U.S.",80.0,9/8/2026,,Hardware,https://example.com/b,Post-IPO,,India,9/9/2026
"""


@pytest.fixture
def fixture_csv(tmp_path):
    path = tmp_path / "layoffs_fixture.csv"
    path.write_text(VALID_ROWS)
    return path


def test_load_returns_expected_columns(fixture_csv):
    df = LayoffsSource(path=fixture_csv).load()
    assert list(df.columns) == list(LayoffsSource().describe_columns())
    assert len(df) == 2


def test_load_preserves_missing_values_as_nan(fixture_csv):
    df = LayoffsSource(path=fixture_csv).load()
    assert pd.isna(df.loc[1, "percentage_laid_off"])
    assert pd.isna(df.loc[1, "funds_raised"])


def test_load_raises_on_missing_column(tmp_path):
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("company,location\nNeo Financial,Calgary\n")
    with pytest.raises(ValueError, match="missing expected columns"):
        LayoffsSource(path=bad_csv).load()


def test_default_path_points_at_data_raw():
    source = LayoffsSource()
    assert source.path.name == "layoffs.csv"
    assert source.path.parent.name == "raw"
