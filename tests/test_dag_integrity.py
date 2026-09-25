"""Structural checks on the Airflow DAG: imports cleanly, has the expected
tasks and dependency edges.

Needs apache-airflow, which the main requirements.txt does not include (see
requirements-airflow.txt and the dedicated CI job) - skipped automatically
if it is not installed, so `pytest -q` still passes without it, same
pattern as test_warehouse_loader.py skipping without a reachable Postgres.

Only checks DAG *structure*. The task bodies themselves import src.* lazily
at task-run time (see warehouse_pipeline_dag.py's docstring), so collecting
the DagBag here never touches pandas/scikit-learn/psycopg2 and never needs
a database - it is a pure parse-time check.
"""

from pathlib import Path

import pytest

# Checks the "airflow.models" submodule specifically, not "airflow": this
# project's own airflow/ directory (airflow/dags/) has no __init__.py, so
# when the real apache-airflow package is NOT installed, Python still
# resolves a bare `import airflow` to it as an (empty) PEP 420 namespace
# package - importorskip("airflow") would then NOT skip, and the fixture
# below would fail with a confusing ModuleNotFoundError instead. The real
# package's airflow.models submodule only exists when apache-airflow is
# actually installed, so checking that leaf module is what actually detects
# "is the real package present".
pytest.importorskip("airflow.models", reason="apache-airflow not installed (see requirements-airflow.txt)")

DAGS_DIR = Path(__file__).resolve().parents[1] / "airflow" / "dags"

EXPECTED_TASK_IDS = {
    "extract_transform_layoffs",
    "extract_transform_ai_jobs",
    "extract_transform_survey",
    "ensure_schema",
    "load_warehouse",
}


@pytest.fixture(scope="module")
def dagbag():
    from airflow.models import DagBag

    return DagBag(dag_folder=str(DAGS_DIR), include_examples=False)


def test_dagbag_has_no_import_errors(dagbag):
    assert dagbag.import_errors == {}


def test_warehouse_dag_is_collected(dagbag):
    assert "ai_job_disruption_warehouse" in dagbag.dags


def test_warehouse_dag_has_expected_tasks(dagbag):
    dag = dagbag.dags["ai_job_disruption_warehouse"]
    assert set(dag.task_ids) == EXPECTED_TASK_IDS


def test_load_warehouse_depends_on_every_upstream_task(dagbag):
    dag = dagbag.dags["ai_job_disruption_warehouse"]
    load_task = dag.get_task("load_warehouse")
    assert set(load_task.upstream_task_ids) == EXPECTED_TASK_IDS - {"load_warehouse"}


def test_extract_tasks_have_no_upstream_dependencies(dagbag):
    dag = dagbag.dags["ai_job_disruption_warehouse"]
    for task_id in ["extract_transform_layoffs", "extract_transform_ai_jobs", "extract_transform_survey", "ensure_schema"]:
        assert dag.get_task(task_id).upstream_task_ids == set()


def test_dag_is_manually_triggered_not_scheduled(dagbag):
    dag = dagbag.dags["ai_job_disruption_warehouse"]
    assert dag.timetable.summary in ("Never, external triggers only", "None")
