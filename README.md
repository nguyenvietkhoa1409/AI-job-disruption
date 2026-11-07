# AI Job Market Disruption

**An integrated analysis of technology layoffs, AI job postings, and developer sentiment.**

Since 2020, technology companies have gone through repeated waves of layoffs while generative AI has become increasingly integrated into software work. This project brings together three public datasets to examine reported workforce reductions, advertised AI-related roles, and developers' views on AI's impact on their work.

The pipeline processes **55,291 raw records** from three sources. After validation, **55,160 records are loaded into a PostgreSQL warehouse** and explored in a Power BI report. The goal is to compare these perspectives at shared sector and role-family levels—not to infer that AI hiring directly replaces jobs lost elsewhere.

**Authors:** [Viet Khoa Nguyen](https://github.com/nguyenvietkhoa1409) & [Mai Anh Tieu](https://github.com/maianhtieu87)

**Full project report:** [Technical and analytical report](https://drive.google.com/file/d/1VmquvspkbcTTeaY8uYWBeI0jAiQKB644/view?usp=drive_link)

## Project at a glance

| Component | Implementation |
|---|---|
| Data sources | Layoffs.fyi tracker, AI job postings, Stack Overflow Developer Survey 2025 |
| Processing | Python 3.12, pandas |
| Data warehouse | PostgreSQL, fact constellation, conformed dimensions, materialized mart |
| Orchestration | Apache Airflow, Docker Compose |
| Text analysis | TF-IDF, non-negative matrix factorization (NMF) |
| BI and testing | Power BI, DAX, SQL, pytest, GitHub Actions |

## Power BI dashboard gallery

The report is organized into **five sections across seven dashboard pages**: Overview, Layoffs (two pages), Role & Creation (two pages), Sentiment, and Cross-source analysis. All dashboard captures are included below; the full project report provides the detailed page-level analysis and methodology.

### 1. Overview

![Overview dashboard](materials/db_1.png)

*Figure 4. Overview dashboard: workforce reductions, emerging roles and practitioner sentiment, with a sector grid and a dot plot of AI-threat rates.*

### 2. Layoffs

![Layoffs dashboard: when and where](materials/db_2a.png)

*Figure 5. Layoffs dashboard (when and where): monthly trend by continent, geographic distribution and sector severity.*

![Layoffs dashboard: who cut most](materials/db_2b.png)

*Figure 6. Layoffs dashboard (who cut most): median reduction by funding stage, shutdown share by year and the weight of the ten largest events.*

### 3. AI roles and creation

![Role and creation dashboard: roles and pay](materials/db_3a.png)

*Figure 7. Role and Creation dashboard (roles and pay): role families by median salary against demand, and pay by title, education and experience.*

![Role and creation dashboard: skills](materials/db_3b.png)

*Figure 8. Role and Creation dashboard (skills): which skills define which role families.*

### 4. Developer sentiment

![Developer sentiment dashboard](materials/db_4.png)

*Figure 9. Sentiment dashboard: favorability, trust, perceived automation threat and the skills expected to remain valuable.*

### 5. Cross-source analysis

![Cross-source dashboard](materials/db_5.png)

*Figure 10. Cross-source dashboard: sector-level cuts against AI postings, and role-family demand growth against practitioner threat perception.*

## Data sources

Each source has a different grain and contributes a distinct perspective. Raw files are not committed to this repository.

| Dataset | Grain | Raw rows | Coverage | Main limitation |
|---|---|---:|---|---|
| [Layoffs.fyi tracker](https://www.kaggle.com/datasets/swaptr/layoffs-2022) | One reported layoff event | 4,600 | 2020-03-11 to 2026-09-08 | Headcount is missing for many events; no role or experience fields |
| [AI Jobs Market 2025–2026 Salaries](https://www.kaggle.com/datasets/alitaqishah/ai-jobs-market-2025-2026-salaries) | One job posting | 1,500 | 2025-01 to 2026-03 | Limited sample; supplied demand indicators are not calculated from the posting time series |
| [Stack Overflow Developer Survey 2025](https://survey.stackoverflow.co/) ([Kaggle CSV copy](https://www.kaggle.com/datasets/edoardogalli/stack-overflow-annual-developer-survey-2025)) | One survey respondent | 49,191 | 2025 survey wave | Self-selected respondents; no respondent-level date |

The pipeline uses 11 fields from Layoffs, 25 from AI Jobs, and 18 from the survey. Missing survey answers are retained as explicit missing categories where appropriate; missing layoff headcounts remain SQL `NULL` and are not imputed.

## Architecture

![End-to-end architecture](materials/image_1.png)

*Figure 1. End-to-end architecture from the public sources to the BI layer. Rejected rows go to a quarantine area, and topic modeling applies to the survey only.*

Raw CSV files pass through dataset-specific Python loaders, quality checks, and transformations. Rejected records are written to quarantine; processed files are loaded into PostgreSQL; and Power BI reads the warehouse and its materialized mart. Airflow orchestrates the ETL and warehouse-load stages in Docker Compose.

### Engineering highlights

- **Reusable ETL:** Shared interfaces support dataset-specific loaders, validation rules, and transformations. Expected columns are checked before processing.
- **Auditable data quality:** Rejected records are quarantined with reasons rather than silently dropped. All raw records are accounted for in the reconciliation below.
- **Conformed dimensions:** Country, industry, role, experience level, and skill labels are standardized across sources to support carefully scoped comparisons.
- **Dimensional warehouse:** Separate fact tables preserve each source's grain. A bridge table resolves the many-to-many relationship between postings and skills; a materialized view pre-aggregates layoffs by country and month.
- **Reliable loading and testing:** The loader uses a single database transaction and is tested for row counts, constraint violations, repeat-load behavior, and mart reconciliation. Unit, integration, and Airflow DAG checks run in GitHub Actions.

### Data quality results

| Dataset | Raw rows | Quarantined | Retained / loaded | Unaccounted |
|---|---:|---:|---:|---:|
| Layoffs | 4,600 | 18 (0.39%) | 4,582 | 0 |
| AI Jobs | 1,500 | 0 (0%) | 1,500 | 0 |
| Stack Overflow Survey | 49,191 | 113 (0.23%) | 49,078 | 0 |
| **Total** | **55,291** | **131 (0.24%)** | **55,160** | **0** |

The 18 quarantined layoff rows were older records from duplicate-event groups; 113 survey responses failed an age-versus-experience plausibility rule. Other candidate rules were rejected after tests showed that they would remove substantial amounts of potentially valid data.

### Warehouse model

![Warehouse entity-relationship diagram](materials/image_3.png)

*Figure 2. Entity-relationship diagram: 8 dimension tables, 4 fact tables and 1 summary view.*

The warehouse keeps the three source subject areas separate while sharing conformed dimensions. It also includes a posting-skill bridge and a country-month summary mart.

## Topic modeling

The survey's `AIOpen` field contains optional free-text responses about skills developers expect to remain valuable as AI advances. Of 22,511 responses that passed quality and spam checks, 15,698 remained after short answers were filtered.

The pipeline converts answers into TF-IDF features and applies NMF to identify ten themes. Labels use anchor-word matching rather than arbitrary topic numbers. If an anchor set matches no topic or multiple topics, the pipeline stops for review instead of silently assigning potentially incorrect labels. The full report documents the filtering choices, topic terms, anchor rules, and model-versioning procedure.

![Topic modeling workflow](materials/image_2.png)

*Figure 3. From raw text to dimensional topic assignments. Dashed borders mark filtered records; the red node is the automatic halt on a label mismatch.*

## Key findings

The findings below are descriptive results from the supplied datasets and should be interpreted within their coverage limitations.

| Area | Selected finding |
|---|---|
| **Overview** | The three datasets provide complementary views of layoffs, AI postings, and developer sentiment within the aligned period. |
| **Layoffs** | In 2025-01 to 2026-03, recorded layoff events were 48.9% lower than in the preceding 15 months, while reported headcount was 1.1% lower. The ten largest events accounted for 54.1% of reported headcount in the window. |
| **AI roles and pay** | Median advertised salary rises from $145,000 at Entry level to $238,000 at Lead level (+64%). Dataset-supplied demand-growth indicators are highest for ML Operations (+53%) and AI Engineering (+40%). |
| **Developer sentiment** | Among survey respondents, 78.5% report using AI at least monthly, 46% distrust its accuracy, and 14.9% view it as a threat to their job. |
| **Cross-source** | Technology & Software represents 33.6% of recorded layoff headcount but 7.8% of AI job postings in the selected datasets. These are shares of different datasets, not directly comparable measures of total sector employment, layoffs, or hiring. |

## Limitations

- **Coverage:** The datasets are snapshots and samples, not a census of technology layoffs, AI hiring, or developers.
- **Missing headcount:** 34.8% of layoff events have no reported headcount. Aggregate headcount figures are lower bounds, and period comparisons may be affected by changes in reporting completeness.
- **Different populations and grains:** Sources are linked through shared categories, not company- or person-level identifiers. Their percentages should not be interpreted as directly comparable market shares.
- **No causal identification:** The analysis cannot establish that AI adoption caused layoffs or that AI vacancies replaced displaced jobs. The survey is a single self-selected wave with no respondent-level date.
- **Static ingestion:** Source files are downloaded and loaded manually; the project does not use streaming or continuously refreshed feeds.

## Getting started

### Requirements

- Python 3.12
- Docker and Docker Compose
- The three raw CSV files listed below

### 1. Install dependencies

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Add raw datasets

Place the downloaded files in `data/raw/`:

```text
data/raw/
├── layoffs.csv
├── ai_jobs_market_2025_2026.csv
└── survey_results_public.csv
```

Then validate the files:

```bash
python validate_sources.py
```

### 3. Run ETL and load PostgreSQL

```bash
cp .env.example .env
# Add local database credentials to .env

docker compose up -d postgres
python run_pipeline.py
python setup_database.py
python -m src.warehouse.loader
```

With the supplied snapshots, the expected loaded counts are 4,582 layoff events, 1,500 job postings, 49,078 survey responses, and 9,419 posting-skill pairs.

### 4. Run with Airflow (optional)

Docker Compose also provides Airflow at [http://localhost:8080](http://localhost:8080). Build and start the services, retrieve the standalone admin password, and trigger the DAG:

```bash
docker compose build airflow
docker compose up -d
docker exec ai_job_disruption_airflow cat /opt/airflow/standalone_admin_password.txt
docker exec ai_job_disruption_airflow airflow dags trigger ai_job_disruption_warehouse
```

The `ai_job_disruption_warehouse` DAG runs the dataset ETL tasks, checks the schema, and loads the warehouse. It is triggered manually and does not reset the schema.

### 5. Run tests

```bash
pytest -q
```

PostgreSQL integration tests require a reachable database configured in `.env` and **drop and recreate the `public` schema**. Use a disposable test database only. The Airflow DAG integrity check runs in the `dag-integrity` GitHub Actions job; the pytest job uses a PostgreSQL 16 service.

## Repository structure

```text
src/                  # Loaders, quality rules, transformations, NMF, EDA, schema, warehouse
schema/               # PostgreSQL DDL and mart SQL
airflow/dags/          # Airflow DAG
reports/              # Data dictionary, EDA notes, and figures
materials/             # README diagrams and dashboard screenshots
tests/                # Unit and integration tests
data/                 # Raw, processed, and quarantine files (gitignored)

run_pipeline.py        # Run ETL without the database
setup_database.py      # Apply SQL schema; --reset rebuilds it
validate_sources.py    # Check raw source files
docker-compose.yml     # PostgreSQL and Airflow services
```

## Contributing

`main` is protected. Work on `feature/*`, `fix/*`, or `docs/*` branches and merge through pull requests. The Git workflow and conflict-handling guidance are documented in `Layoff Project.md`.



