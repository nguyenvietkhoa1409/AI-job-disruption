"""Smoke test the three data sources against the real files under data/raw/.

Not part of the pytest suite: CI never has the real datasets (data/raw/ is
gitignored), so this is run manually/locally after placing the raw CSVs.
"""

import sys

from src.data_sources.ai_jobs_source import AIJobsSource
from src.data_sources.layoffs_source import LayoffsSource
from src.data_sources.survey_source import SurveySource

SOURCES = [LayoffsSource, AIJobsSource, SurveySource]


def validate(source_cls) -> bool:
    name = source_cls.__name__
    try:
        df = source_cls().load()
    except (FileNotFoundError, ValueError) as exc:
        print(f"[FAIL] {name}: {exc}")
        return False

    missing_pct = (df.isna().mean() * 100).round(1)
    top_missing = missing_pct[missing_pct > 0].sort_values(ascending=False)

    print(f"[OK]   {name}: {df.shape[0]} rows x {df.shape[1]} columns")
    if not top_missing.empty:
        preview = ", ".join(f"{col}={pct}%" for col, pct in top_missing.items())
        print(f"       missing: {preview}")
    return True


def main() -> int:
    results = [validate(source_cls) for source_cls in SOURCES]
    if not all(results):
        print("\nvalidate_sources: FAILED")
        return 1
    print("\nvalidate_sources: all sources loaded successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
