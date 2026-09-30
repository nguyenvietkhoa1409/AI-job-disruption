# AI Job Market Disruption

An end-to-end Data Engineering + Data Analytics project investigating how AI is reshaping the tech labor market, combining three public datasets that represent three angles of the same disruption:

- **Layoffs** (Layoffs.fyi, via Kaggle) — what is being cut
- **AI Jobs Market 2025-2026 Salaries** (Kaggle) — what is being created
- **Stack Overflow Developer Survey 2025** — how practitioners feel about it

## Pipeline stages

1. **Data sources** — three public datasets collected as batch files.
2. **Ingestion and raw storage** — loaded into `data/raw/` with no transformation applied.
3. **Cleaning and EDA** — each dataset profiled, cleaned, and explored independently.
4. **Warehouse and transform** — cleaned data modeled into a shared star schema in PostgreSQL.
5. **Analytics and delivery** — SQL analysis, BI dashboard, and a written insight report.

## Project structure

```
src/
├── data_sources/        # BaseDataSource + per-dataset loaders
├── quality/              # BaseQualityRuleSet + per-dataset quality rules
├── preprocessing/        # BaseTransformer + per-dataset cleaning transforms
├── feature_engineering/  # BaseFeatureEngineer + SurveyFeatureEngineer (NMF topics)
├── eda/                  # DatasetProfiler, EDAVisualizer
├── schema/                # dimension maps + star schema dataclasses
├── warehouse/loader.py    # WarehouseLoader: processed CSVs -> Postgres star schema
├── pipeline.py            # DatasetPipeline: chains the interfaces above
└── config.py               # ProjectPaths

schema/                    # SQL run by Postgres: 001 dimensions, 002 facts, 003-004 marts, 005 views, 006 pipeline_run_log
airflow/dags/              # warehouse_pipeline_dag.py
data/{raw,processed,quarantine}/   # not committed, see .gitignore
reports/{data_dictionary,figures}/
tests/

run_pipeline.py            # extract/clean/transform all 3 datasets (no database)
setup_database.py          # apply schema/*.sql; --reset rebuilds from scratch
validate_sources.py        # smoke test that the raw files load
docker-compose.yml         # postgres (5432) + airflow standalone (8080)
Dockerfile.airflow         # Airflow image with this project's dependencies
requirements-airflow.txt   # DAG-test dependencies (CI dag-integrity job)
```

`schema/` (root) holds the SQL that Postgres executes; `src/schema/` is the Python mirror of the same contract (`tests/test_star_schema.py` keeps the two in sync).

## Setup

Requires **Python 3.12.x** (CI and `requirements.txt` pins are tested against 3.12; `numpy==2.5.3` has no wheels for 3.11 or earlier).

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest
```

## Contributing

See the Git/GitHub team playbook in `Layoff Project.md` for the branching model, PR flow, and conflict-handling procedures. `main` is protected; all work happens on `feature/*` or `fix/*` branches merged via PR.

## Data

Raw datasets are not committed to this repository (see `.gitignore`). Place source CSVs under `data/raw/` locally:

- `layoffs.csv`
- `ai_jobs_market_2025_2026.csv`
- `survey_results_public.csv` / `survey_results_public-selected-columns.csv`

After placing the files, smoke test that all three sources load against the real data (this is not part of `pytest`, since CI never has the real files):

```
python validate_sources.py
```

## Database (Docker + PostgreSQL)

The star schema (`schema/001_dimensions.sql`, `002_facts.sql`, `003_mart_country_industry_month.sql`, `004_marts.sql`, `005_views.sql`, `006_pipeline_run_log.sql`) runs on a local PostgreSQL container.

```
cp .env.example .env
docker compose up -d postgres
docker compose ps          # wait for postgres to report "healthy"
```

(`docker compose up -d` without a service name also builds and starts Airflow, see [Run with Airflow](#run-with-airflow).)

On first startup (empty volume), the postgres image auto-runs every `.sql` file under `schema/` in filename order, so the 8 dimension tables, 4 fact tables, the `pipeline_run_log` table, 4 materialized views (`mart_country_industry_month`, `mart_industry_overview`, `mart_country_overview`, `mart_sector_share_gap`) and the dashboard views (`vw_*`) all exist right away. Verify with:

```
docker exec -it ai_job_disruption_pg psql -U airflow -d ai_job_disruption -c "\dt" -c "\dm"
```

Replace `airflow` with your `POSTGRES_USER` if you changed it in `.env`. `\dt` lists 13 tables (8 dimensions + 4 facts + the operational `pipeline_run_log`); the marts are materialized views, so they only show under `\dm`, and the `vw_*` views under `\dv`. Tables are empty until the loader runs. `docker exec` connects inside the container and skips the password; external clients (Python loader, DBeaver) connect to `localhost:5432` with the password from `.env`.

The auto-run only happens on an empty volume, so a volume created before a schema change keeps the old tables and the loader then fails on missing columns. Rebuild the schema once with `python setup_database.py --reset` (or `docker compose down -v`).

Postgres only reads `POSTGRES_PASSWORD` when it first creates the database. To change it later, edit `.env`, then recreate the volume (this wipes all data):

```
docker compose down -v
docker compose up -d
```

`.env` holds real local credentials and is gitignored - never commit it. `.env.example` is the template teammates copy from.

## Run the loader

With the raw files in `data/raw/` and Postgres running:

```
python run_pipeline.py              # steps 1-4 -> data/processed/*.csv (+ survey_topics.csv)
python setup_database.py            # idempotent; use --reset after any table change (drops all data)
python -m src.warehouse.loader      # loads dims -> facts -> bridge -> refreshes the marts -> logs the run
```

The loader runs as one transaction (everything loads or nothing does) and prints the rows inserted per table. Every table has a natural key with `ON CONFLICT DO NOTHING`, so re-running it inserts 0 rows. With the current raw files the first load gives:

| Table | Rows |
|---|---|
| dim_country / dim_industry / dim_company / dim_role | 175 / 12 / 2,984 / 57 |
| dim_ai_sentiment / dim_skill / dim_ai_open_topic | 641 / 91 / 10 |
| fact_layoff_event / fact_job_posting / fact_survey_response | 4,582 / 1,500 / 49,078 |
| fact_job_posting_skill | 9,419 |

`mart_country_industry_month` sums to 4,582 layoff events. Because existing rows are never overwritten, a loader fix only reaches rows that were already loaded after `python setup_database.py --reset` and a fresh load (dev database only).

## Run with Airflow

`docker compose up -d` also starts a single-container Airflow (`airflow standalone`) at http://localhost:8080. The DAG `ai_job_disruption_warehouse` runs `extract_transform_{layoffs,ai_jobs,survey}` and `ensure_schema`, then `load_warehouse` as a single transactional task. It is triggered manually (`schedule=None`) and never resets the schema.

```
docker compose build airflow        # first time, or after requirements.txt changes
docker compose up -d
docker logs -f ai_job_disruption_airflow     # wait for "Airflow is ready", then Ctrl+C
docker exec ai_job_disruption_airflow cat /opt/airflow/standalone_admin_password.txt
```

Log in as `admin` with that password, or trigger from the CLI:

```
docker exec ai_job_disruption_airflow airflow dags list-import-errors
docker exec ai_job_disruption_airflow airflow dags unpause ai_job_disruption_warehouse
docker exec ai_job_disruption_airflow airflow dags trigger ai_job_disruption_warehouse
docker exec ai_job_disruption_airflow airflow dags list-runs -d ai_job_disruption_warehouse
```

The project root is mounted into the container, so the extract tasks write `data/processed/`, `data/quarantine/` and `reports/` on the host. The Airflow image installs `requirements.txt` without Airflow's constraints file (pandas 3.x vs the constraint pin 2.1.4); pip prints a conflict warning for the Google/Snowflake providers, which the DAG does not use.

## Tests

```
pytest -q
```

The loader integration tests (`tests/test_warehouse_loader.py`) run only when a Postgres from `.env` is reachable and skip silently otherwise. They **drop and recreate the `public` schema**, so never point `.env` at a database whose data matters; reload afterwards with `python setup_database.py --reset` and `python -m src.warehouse.loader`.

`tests/test_dag_integrity.py` needs `apache-airflow` and is skipped without it. Airflow does not run natively on Windows, so run it the way the CI `dag-integrity` job does, in a Python 3.12 container:

```
docker run --rm -v "${PWD}:/src:ro" -w /src python:3.12-slim bash -c "pip install -q -r requirements-airflow.txt && pytest -q -p no:cacheprovider tests/test_dag_integrity.py"
```

CI (`.github/workflows/tests.yml`) runs two jobs: `pytest` (with a `postgres:16` service) and `dag-integrity`.
