"""Tests for BaseDataSource."""

import pandas as pd
import pytest

from src.data_sources.base_source import BaseDataSource


class _DummySource(BaseDataSource):
    def load(self) -> pd.DataFrame:
        return pd.DataFrame({"a": [1], "b": [2]})

    def describe_columns(self) -> dict[str, str]:
        return {"a": "int64", "b": "int64"}


def test_base_data_source_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseDataSource()


def test_subclass_missing_abstract_method_cannot_be_instantiated():
    class _IncompleteSource(BaseDataSource):
        def load(self) -> pd.DataFrame:
            return pd.DataFrame()

    with pytest.raises(TypeError):
        _IncompleteSource()


def test_concrete_subclass_loads_dataframe():
    df = _DummySource().load()
    assert list(df.columns) == ["a", "b"]


def test_validate_passes_when_all_expected_columns_present():
    source = _DummySource()
    source.validate(source.load())  # should not raise


def test_validate_raises_on_missing_columns():
    source = _DummySource()
    df = pd.DataFrame({"a": [1]})
    with pytest.raises(ValueError, match="missing expected columns"):
        source.validate(df)
