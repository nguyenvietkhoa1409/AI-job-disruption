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
├── feature_engineering/  # BaseFeatureEngineer + per-dataset feature steps
├── eda/                  # DatasetProfiler, EDAVisualizer
├── schema/                # dimension maps + star schema dataclasses
├── pipeline.py            # DatasetPipeline: chains the interfaces above
└── config.py               # ProjectPaths

data/{raw,processed,quarantine}/   # not committed, see .gitignore
reports/{data_dictionary,figures}/
tests/
```

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
