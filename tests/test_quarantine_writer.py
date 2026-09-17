"""Tests for QuarantineWriter, isolated from the real data/quarantine/ directory."""

import pandas as pd
import pytest

from src.quality.quarantine_writer import QuarantineWriter


@pytest.fixture
def quarantine_df():
    return pd.DataFrame([
        {"company": "Bad Pct", "quarantine_reason": "percentage_laid_off_out_of_range"},
        {"company": "Multi", "quarantine_reason": "total_laid_off_negative, funds_raised_negative"},
    ])


def test_write_creates_output_dir_and_csv(tmp_path, quarantine_df):
    writer = QuarantineWriter(output_dir=tmp_path / "quarantine")
    path = writer.write("layoffs", quarantine_df)

    assert path == tmp_path / "quarantine" / "layoffs.csv"
    written = pd.read_csv(path)
    assert list(written["company"]) == ["Bad Pct", "Multi"]


def test_write_overwrites_on_repeat_runs(tmp_path, quarantine_df):
    writer = QuarantineWriter(output_dir=tmp_path)
    writer.write("layoffs", quarantine_df)
    path = writer.write("layoffs", quarantine_df.iloc[:1])

    written = pd.read_csv(path)
    assert len(written) == 1


def test_write_empty_quarantine_produces_header_only_file(tmp_path):
    writer = QuarantineWriter(output_dir=tmp_path)
    empty = pd.DataFrame(columns=["company", "quarantine_reason"])
    path = writer.write("layoffs", empty)

    written = pd.read_csv(path)
    assert len(written) == 0
    assert list(written.columns) == ["company", "quarantine_reason"]


def test_summarize_counts_multi_rule_rows_under_each_rule(quarantine_df):
    counts = QuarantineWriter.summarize(quarantine_df)

    assert counts == {
        "percentage_laid_off_out_of_range": 1,
        "total_laid_off_negative": 1,
        "funds_raised_negative": 1,
    }


def test_summarize_empty_quarantine_returns_empty_dict():
    empty = pd.DataFrame(columns=["company", "quarantine_reason"])
    assert QuarantineWriter.summarize(empty) == {}
