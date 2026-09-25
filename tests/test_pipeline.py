"""Tests for DatasetPipeline.run()."""

import pandas as pd
import pytest

from src.config import ProjectPaths
from src.data_sources.base_source import BaseDataSource
from src.data_sources.layoffs_source import LayoffsSource
from src.eda.profiler import DatasetProfiler
from src.pipeline import DatasetPipeline
from src.preprocessing.base_transformer import BaseTransformer
from src.preprocessing.layoffs_transformer import LayoffsTransformer
from src.quality.base_rule_set import BaseQualityRuleSet
from src.quality.layoffs_rules import LayoffsQualityRules


class _DummySource(BaseDataSource):
    def load(self) -> pd.DataFrame:
        return pd.DataFrame({"id": [1, 2, 3], "value": [10, -5, 20]})

    def describe_columns(self) -> dict[str, str]:
        return {"id": "int64", "value": "int64"}


class _DummyQualityRules(BaseQualityRuleSet):
    def apply(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        return self._split(df, {"value_negative": df["value"] < 0})


class _DummyTransformer(BaseTransformer):
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["value_doubled"] = df["value"] * 2
        return df


def _make_pipeline(name="widgets"):
    return DatasetPipeline(name, _DummySource(), _DummyQualityRules(), _DummyTransformer(), DatasetProfiler())


@pytest.fixture(autouse=True)
def _isolate_project_paths(tmp_path, monkeypatch):
    """Redirect PROJECT_PATHS everywhere run() and QuarantineWriter read it,
    so these tests never touch the real data/ folders."""
    fake_paths = ProjectPaths(root=tmp_path)
    monkeypatch.setattr("src.pipeline.PROJECT_PATHS", fake_paths)
    monkeypatch.setattr("src.quality.quarantine_writer.PROJECT_PATHS", fake_paths)


def test_run_writes_processed_csv_with_transformed_columns(tmp_path):
    result = _make_pipeline().run()

    assert result.processed_path == tmp_path / "data" / "processed" / "widgets.csv"
    written = pd.read_csv(result.processed_path)
    assert list(written["value_doubled"]) == [20, 40]  # only the 2 clean rows (value >= 0)


def test_run_writes_quarantine_csv_for_failing_rows(tmp_path):
    result = _make_pipeline().run()

    assert result.quarantine_path == tmp_path / "data" / "quarantine" / "widgets.csv"
    assert result.quarantine_rows == 1
    written = pd.read_csv(result.quarantine_path)
    assert written.loc[0, "quarantine_reason"] == "value_negative"


def test_run_returns_quarantine_summary_and_data_dictionary():
    result = _make_pipeline().run()

    assert result.quarantine_summary == {"value_negative": 1}
    assert set(result.data_dictionary["column"]) == {"id", "value", "value_doubled"}


def test_run_overwrites_processed_and_quarantine_on_repeat_runs():
    pipeline = _make_pipeline()
    pipeline.run()
    result = pipeline.run()

    assert result.clean_rows == 2
    assert result.quarantine_rows == 1


def test_run_end_to_end_with_real_layoffs_classes(tmp_path):
    """Same chain, but with the actual production Source/Rules/Transformer -
    not the dummies above - to prove the real classes wire together."""
    raw_csv = tmp_path / "layoffs_raw.csv"
    pd.DataFrame(
        [
            {
                "company": "Acme", "location": "SF", "total_laid_off": 100, "date": "2024-01-05",
                "percentage_laid_off": 0.10, "industry": "AI", "source": "TechCrunch", "stage": "Series D",
                "funds_raised": 500.0, "country": "United States", "date_added": "2024-01-06",
            },
            {
                "company": "Bad Pct Inc", "location": "NYC", "total_laid_off": 20, "date": "2024-03-01",
                "percentage_laid_off": 55.0, "industry": "AI", "source": "Reuters", "stage": "Seed",
                "funds_raised": 10.0, "country": "United States", "date_added": "2024-03-02",
            },
        ]
    ).to_csv(raw_csv, index=False)

    pipeline = DatasetPipeline(
        "layoffs", LayoffsSource(path=raw_csv), LayoffsQualityRules(), LayoffsTransformer(), DatasetProfiler()
    )
    result = pipeline.run()

    assert result.clean_rows == 1
    assert result.quarantine_rows == 1
    assert "country_canonical" in result.processed.columns

class _DummyFeatureEngineer:
    """Duck-typed stand-in for a BaseFeatureEngineer with one side table."""

    def engineer(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["value_tripled"] = df["value"] * 3
        return df

    def artifacts(self) -> dict[str, pd.DataFrame]:
        return {"lookup": pd.DataFrame({"k": [1], "v": ["a"]})}


def test_run_applies_feature_engineer_and_writes_its_artifacts(tmp_path):
    pipeline = DatasetPipeline(
        "widgets", _DummySource(), _DummyQualityRules(), _DummyTransformer(), DatasetProfiler(), _DummyFeatureEngineer()
    )
    result = pipeline.run()

    assert list(pd.read_csv(result.processed_path)["value_tripled"]) == [30, 60]
    assert result.artifact_paths["lookup"] == tmp_path / "data" / "processed" / "widgets_lookup.csv"
    assert list(pd.read_csv(result.artifact_paths["lookup"])["v"]) == ["a"]


def test_run_without_feature_engineer_writes_no_artifacts():
    assert _make_pipeline().run().artifact_paths == {}