"""Run the full DatasetPipeline (source -> quality -> quarantine -> transform
-> processed CSV -> profile) for all three datasets.

Requires the real raw CSVs under data/raw/ (gitignored, not part of CI) -
same precondition as validate_sources.py. Writes data/processed/<name>.csv
and data/quarantine/<name>.csv for each dataset, overwriting on every run.
"""

import sys

from src.data_sources.ai_jobs_source import AIJobsSource
from src.data_sources.layoffs_source import LayoffsSource
from src.data_sources.survey_source import SurveySource
from src.eda.profiler import DatasetProfiler
from src.pipeline import DatasetPipeline
from src.preprocessing.ai_jobs_transformer import AIJobsTransformer
from src.preprocessing.layoffs_transformer import LayoffsTransformer
from src.preprocessing.survey_transformer import SurveyTransformer
from src.quality.ai_jobs_rules import AIJobsQualityRules
from src.quality.layoffs_rules import LayoffsQualityRules
from src.quality.survey_rules import SurveyQualityRules

PIPELINES = [
    DatasetPipeline("layoffs", LayoffsSource(), LayoffsQualityRules(), LayoffsTransformer(), DatasetProfiler()),
    DatasetPipeline("ai_jobs", AIJobsSource(), AIJobsQualityRules(), AIJobsTransformer(), DatasetProfiler()),
    DatasetPipeline("survey", SurveySource(), SurveyQualityRules(), SurveyTransformer(), DatasetProfiler()),
]


def main() -> int:
    ok = True
    for pipeline in PIPELINES:
        try:
            result = pipeline.run()
        except (FileNotFoundError, ValueError) as exc:
            print(f"[FAIL] {pipeline.name}: {exc}")
            ok = False
            continue

        print(
            f"[OK]   {pipeline.name}: {result.clean_rows} clean / "
            f"{result.quarantine_rows} quarantined -> {result.processed_path}"
        )
        if result.quarantine_summary:
            top = ", ".join(f"{rule}={count}" for rule, count in result.quarantine_summary.items())
            print(f"       quarantine reasons: {top}")

    if not ok:
        print("\nrun_pipeline: FAILED - place the raw CSVs under data/raw/ (see README) and retry")
        return 1
    print("\nrun_pipeline: all datasets processed")
    return 0


if __name__ == "__main__":
    sys.exit(main())