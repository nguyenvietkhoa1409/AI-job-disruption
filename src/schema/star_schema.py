"""Python-side description of the warehouse star schema: 4 fact, 8 dimension tables.

This module and schema/*.sql describe the SAME schema from two sides:
- schema/*.sql is what Postgres executes (types, FKs, CHECK/UNIQUE
  constraints, indexes). It is the source of truth for the database.
- This module is what Python code imports: the loader uses the column lists
  to select/rename DataFrame columns and natural_key to build
  ON CONFLICT clauses, without parsing SQL. It carries no types or
  constraints on purpose.
tests/test_star_schema.py parses schema/*.sql and fails if the two drift
(a table or column added/renamed on one side only).

One dimension more than Layoff Project.md's "4 fact / 7 dim" target, and
not the same tables as first sketched: fact_job_posting_skill + dim_skill
(needed once PR #14 normalized required_skills into a multi-value field),
dim_ai_sentiment and dim_ai_open_topic replace fact_survey_topics /
dim_experience_level / dim_funding_stage. dim_ai_open_topic is the 8th: see
its note below.

Design decisions, each verified against the real processed data:
- dim_role's grain is role identity. experience_level_canonical recurs across
  many postings/respondents of the same role, so it lives on the facts.
  job_category and is_llm_role are constant per job_title (25/25), so they
  live on dim_role, not on fact_job_posting.
- dim_company's grain is company identity. Funding stage changes over time
  (161/2,984 companies), so stage lives on fact_layoff_event.
- fact_layoff_event uses dim_date twice (role-playing): date_key = layoff
  date, date_added_key = when layoffs.fyi recorded it.
- dim_date.date_key is YYYYMMDD and the table is pre-seeded 2020-2030, so
  loaders compute keys instead of looking them up. AI Jobs postings (year +
  month only) map to the 1st of the month.
- dim_ai_sentiment is a junk dimension bundling AIThreat/AISelect/AISent/
  AIAcc (641 combinations) behind one FK.
- fact_survey_response.experience_level_canonical is bucketed from WorkExp
  with EXPERIENCE_BUCKET_BINS (same Entry/Mid/Senior/Lead boundaries as
  EXPERIENCE_MAP), not YearsCode, so AI Jobs and Survey compare on equal
  footing.
- fact_survey_response's natural key is (survey_year, response_id):
  ResponseId restarts every survey wave.
- fact_job_posting_skill is a factless bridge resolving
  required_skills_normalized into one row per (posting, skill).
- dim_ai_open_topic stores each AIOpen topic once per model_version, with
  its top terms as evidence for the label. SurveyFeatureEngineer assigns
  labels by matching anchor terms against each topic's top terms, not by
  NMF component index: a refit on changed data reordered or merged topics in
  7 of 10 trials, which index-based labels would have mislabelled silently.
"""

from dataclasses import dataclass, field


@dataclass
class DimTable:
    name: str
    columns: list[str]
    # Business key the loader matches on (ON CONFLICT target). Mirrors the
    # table's UNIQUE constraint in schema/001_dimensions.sql.
    natural_key: list[str] = field(default_factory=list)


@dataclass
class FactTable:
    name: str
    columns: list[str]
    foreign_keys: list[str]
    # Mirrors the table's UNIQUE / PRIMARY KEY in schema/002_facts.sql.
    natural_key: list[str] = field(default_factory=list)


# --- Dimension tables (8) ---------------------------------------------------

DIM_DATE = DimTable(
    name="dim_date",
    columns=["date_key", "full_date", "year", "quarter", "month", "month_name", "day"],
    natural_key=["full_date"],
)

DIM_COUNTRY = DimTable(
    name="dim_country",
    # continent: enrichment derived from country_converter alongside
    # COUNTRY_MAP, useful for the layoff trend map tile.
    columns=["country_key", "country_canonical", "continent"],
    natural_key=["country_canonical"],
)

DIM_INDUSTRY = DimTable(
    name="dim_industry",
    columns=["industry_key", "industry_sector"],
    natural_key=["industry_sector"],
)

DIM_ROLE = DimTable(
    name="dim_role",
    # role_source: 'job_title' (AI Jobs) or 'DevType' (Survey). job_category
    # and is_llm_role are AI Jobs-only, NULL for Survey rows.
    columns=["role_key", "role_source", "role_title", "role_category", "job_category", "is_llm_role"],
    natural_key=["role_source", "role_title"],
)

DIM_COMPANY = DimTable(
    name="dim_company",
    columns=["company_key", "company_name"],
    natural_key=["company_name"],
)

DIM_AI_SENTIMENT = DimTable(
    name="dim_ai_sentiment",
    columns=["ai_sentiment_key", "ai_threat", "ai_select", "ai_sent", "ai_acc"],
    natural_key=["ai_threat", "ai_select", "ai_sent", "ai_acc"],
)

DIM_SKILL = DimTable(
    name="dim_skill",
    columns=["skill_key", "skill_name"],
    natural_key=["skill_name"],
)

DIM_AI_OPEN_TOPIC = DimTable(
    name="dim_ai_open_topic",
    columns=["ai_open_topic_key", "model_version", "component_id", "topic_label", "top_terms"],
    natural_key=["model_version", "component_id"],
)

DIM_TABLES: list[DimTable] = [
    DIM_DATE,
    DIM_COUNTRY,
    DIM_INDUSTRY,
    DIM_ROLE,
    DIM_COMPANY,
    DIM_AI_SENTIMENT,
    DIM_SKILL,
    DIM_AI_OPEN_TOPIC,
]


# --- Fact tables (4) ---------------------------------------------------------

FACT_LAYOFF_EVENT = FactTable(
    name="fact_layoff_event",
    columns=[
        "layoff_event_key",
        "date_key",
        "date_added_key",
        "company_key",
        "country_key",
        "industry_key",
        "location",
        "stage",
        "total_laid_off",
        "percentage_laid_off",
        "funds_raised_usd_millions",
        "source_url",
    ],
    foreign_keys=["date_key", "date_added_key", "company_key", "country_key", "industry_key"],
    natural_key=["company_key", "date_key", "location"],
)

FACT_JOB_POSTING = FactTable(
    name="fact_job_posting",
    columns=[
        "job_posting_key",
        "job_id",
        "date_key",
        "role_key",
        "country_key",
        "industry_key",
        "city",
        "company_size",
        "remote_work",
        "education_required",
        "experience_level_canonical",
        "years_of_experience",
        "annual_salary_usd",
        "salary_min_usd",
        "salary_max_usd",
        "ai_salary_premium_pct",
        "demand_score",
        "demand_growth_yoy_pct",
        "benefits_score_10",
        "is_senior",
        "is_remote_friendly",
        "salary_tier",
    ],
    foreign_keys=["date_key", "role_key", "country_key", "industry_key"],
    natural_key=["job_id"],
)

FACT_SURVEY_RESPONSE = FactTable(
    name="fact_survey_response",
    columns=[
        "response_key",
        "survey_year",
        "response_id",
        "role_key",
        "country_key",
        "industry_key",
        "ai_sentiment_key",
        "main_branch",
        "age_bucket",
        "ed_level",
        "employment",
        "remote_work",
        "work_exp",
        "years_code",
        "experience_level_canonical",
        "converted_comp_yearly_winsorized",
        "job_sat",
        "ai_open_topic_key",
    ],
    foreign_keys=["role_key", "country_key", "industry_key", "ai_sentiment_key", "ai_open_topic_key"],
    natural_key=["survey_year", "response_id"],
)

# Factless bridge: no measures, one row per (job_posting, skill) pair.
FACT_JOB_POSTING_SKILL = FactTable(
    name="fact_job_posting_skill",
    columns=["job_posting_key", "skill_key"],
    foreign_keys=["job_posting_key", "skill_key"],
    natural_key=["job_posting_key", "skill_key"],
)

FACT_TABLES: list[FactTable] = [
    FACT_LAYOFF_EVENT,
    FACT_JOB_POSTING,
    FACT_SURVEY_RESPONSE,
    FACT_JOB_POSTING_SKILL,
]
