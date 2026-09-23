"""Tests for DatasetProfiler."""

import pandas as pd

from src.eda.profiler import DatasetProfiler


def test_profile_reports_dtype_missing_and_unique_per_column():
    df = pd.DataFrame({
        "a": [1, 2, 2, None],
        "b": ["x", "y", "y", "y"],
    })
    result = DatasetProfiler().profile(df)

    a_row = result.loc[result["column"] == "a"].iloc[0]
    assert a_row["missing_count"] == 1
    assert a_row["missing_pct"] == 25.0
    assert a_row["unique_count"] == 2  # dropna: {1, 2}
    assert a_row["min"] == 1
    assert a_row["max"] == 2

    b_row = result.loc[result["column"] == "b"].iloc[0]
    assert b_row["missing_count"] == 0
    assert b_row["unique_count"] == 2


def test_profile_min_max_are_na_for_non_numeric_columns():
    df = pd.DataFrame({"label": ["x", "y"]})
    result = DatasetProfiler().profile(df)

    row = result.iloc[0]
    assert pd.isna(row["min"])
    assert pd.isna(row["max"])


def test_profile_handles_all_missing_numeric_column():
    df = pd.DataFrame({"n": pd.Series([None, None, None], dtype="float64")})
    result = DatasetProfiler().profile(df)

    row = result.iloc[0]
    assert row["missing_count"] == 3
    assert row["missing_pct"] == 100.0
    assert row["unique_count"] == 0
    assert pd.isna(row["min"])
    assert pd.isna(row["max"])


def test_profile_empty_dataframe_does_not_divide_by_zero():
    df = pd.DataFrame({"a": pd.Series(dtype="float64")})
    result = DatasetProfiler().profile(df)

    assert result.loc[0, "missing_pct"] == 0.0


def test_profile_one_row_per_column_in_original_order():
    df = pd.DataFrame({"z": [1], "a": [2], "m": [3]})
    result = DatasetProfiler().profile(df)

    assert list(result["column"]) == ["z", "a", "m"]