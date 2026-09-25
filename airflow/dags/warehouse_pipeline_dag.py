"""Warehouse pipeline DAG: extract/transform the 3 datasets, then load the
star schema and refresh the mart.

schedule=None (manually triggered): all 3 sources are static snapshots
(Kaggle layoffs mirror, a fixed AI Jobs Market export, one Stack Overflow
Developer Survey wave) - there is no live feed to run this on a cron for.

Every task is a thin wrapper that imports and calls code already tested
outside Airflow (src.pipeline.DatasetPipeline, src.warehouse.loader) -
this file adds no new logic of its own, per Layoff Project.md 7.2: "Keep
DAG code deterministic and testable outside the Airflow scheduler when
possible." Imports of src.* are deferred to inside each task body (not at
module level) so the scheduler can parse this file quickly without paying
pandas/scikit-learn's import cost on every DAG-folder scan.

load_warehouse is a single task, not four (dims/facts/bridge/mart): the
whole point of WarehouseLoader.run() is that it wraps all four in one
Postgres transaction (either everything loads or nothing does) - splitting
it into separate Airflow tasks would break that guarantee, since each task
would open its own connection/transaction.
"""

from __future__ import annotations

import datetime as dt

from airflow.decorators import dag, task

DEFAULT_ARGS = {
    "owner": "ai-job-disruption",
    "retries": 1,
    "retry_delay": dt.timedelta(minutes=2),
}


@dag(
    dag_id="ai_job_disruption_warehouse",
    description="Extract/transform the 3 datasets, load the star schema, refresh the mart.",
    schedule=None,
    start_date=dt.datetime(2024, 1, 1),
    catchup=False,
    default_args=DEFAULT_ARGS,
    tags=["ai-job-disruption", "warehouse"],
)
def warehouse_pipeline():
    @task
    def extract_transform_layoffs() -> None:
        from src.data_sources.layoffs_source import LayoffsSource
        from src.eda.profiler import DatasetProfiler
        from src.pipeline import DatasetPipeline
        from src.preprocessing.layoffs_transformer import LayoffsTransformer
        from src.quality.layoffs_rules import LayoffsQualityRules

        DatasetPipeline(
            "layoffs", LayoffsSource(), LayoffsQualityRules(), LayoffsTransformer(), DatasetProfiler()
        ).run()

    @task
    def extract_transform_ai_jobs() -> None:
        from src.data_sources.ai_jobs_source import AIJobsSource
        from src.eda.profiler import DatasetProfiler
        from src.pipeline import DatasetPipeline
        from src.preprocessing.ai_jobs_transformer import AIJobsTransformer
        from src.quality.ai_jobs_rules import AIJobsQualityRules

        DatasetPipeline(
            "ai_jobs", AIJobsSource(), AIJobsQualityRules(), AIJobsTransformer(), DatasetProfiler()
        ).run()

    @task
    def extract_transform_survey() -> None:
        from src.data_sources.survey_source import SurveySource
        from src.eda.profiler import DatasetProfiler
        from src.feature_engineering.survey_feature_engineer import SurveyFeatureEngineer
        from src.pipeline import DatasetPipeline
        from src.preprocessing.survey_transformer import SurveyTransformer
        from src.quality.survey_rules import SurveyQualityRules

        DatasetPipeline(
            "survey", SurveySource(), SurveyQualityRules(), SurveyTransformer(), DatasetProfiler(),
            SurveyFeatureEngineer(),
        ).run()

    @task
    def ensure_schema() -> None:
        """Idempotent (IF NOT EXISTS / ON CONFLICT DO NOTHING throughout
        schema/*.sql). Deliberately never --reset here: a scheduled or
        manually triggered DAG run must never be able to drop tables -
        --reset is a human-at-a-terminal-only operation (setup_database.py)."""
        import os
        from pathlib import Path

        import psycopg2
        from dotenv import load_dotenv

        load_dotenv()
        # Not derived from __file__: dags/ is bind-mounted at
        # /opt/airflow/dags (see docker-compose.yml), a different container
        # path than the project root, which is mounted separately at
        # /opt/project (also PYTHONPATH, so schema/ lives right under it).
        schema_dir = Path("/opt/project/schema")
        conn = psycopg2.connect(
            host=os.environ.get("POSTGRES_HOST", "localhost"),
            port=os.environ.get("POSTGRES_PORT", "5432"),
            dbname=os.environ["POSTGRES_DB"],
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
        )
        try:
            with conn, conn.cursor() as cur:
                for path in sorted(schema_dir.glob("*.sql")):
                    cur.execute(path.read_text(encoding="utf-8"))
        finally:
            conn.close()

    @task
    def load_warehouse() -> dict[str, int]:
        from src.warehouse.loader import run_full_load

        counts = run_full_load()
        print(f"load_warehouse: {counts}")
        return counts

    extracted = [extract_transform_layoffs(), extract_transform_ai_jobs(), extract_transform_survey()]
    schema_ready = ensure_schema()
    loaded = load_warehouse()

    [*extracted, schema_ready] >> loaded


warehouse_pipeline()
