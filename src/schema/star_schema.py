"""Dataclasses describing the fact/dimension tables of the warehouse star schema.

4 fact tables, 7 dimension tables. Deliberately one more fact and one more
dim than Layoff Project.md's original "4 fact / 7 dim" target implies on its
own: fact_job_posting_skill + dim_skill only became necessary once PR #14
(feature/text-mining-features) normalized required_skills into a multi-value
field, after that count had already been frozen in the spec. Documented here
rather than silently drifting from the written target.

Design decisions worth knowing before editing this file:
- dim_role does NOT carry experience_level. A role_title (job_title/DevType)
  recurs across many postings/respondents at different experience levels, so
  folding experience into dim_role would break its grain (no longer one row
  per role identity). experience_level_canonical instead lives as a
  degenerate attribute directly on fact_job_posting and fact_survey_response.
- fact_survey_response.experience_level_canonical is bucketed from WorkExp
  (professional experience, the analytical equivalent of AI Jobs'
  years_of_experience) using the same Entry(0-2)/Mid(3-5)/Senior(6-9)/
  Lead(10+) boundaries as EXPERIENCE_MAP, not YearsCode (includes hobbyist
  coding) - added so the salary/role comparison tile can compare AI Jobs and
  Survey on equal footing instead of confounding role category with tenure.
- dim_ai_sentiment is a junk dimension bundling AIThreat/AISelect/AISent/AIAcc
  (correlated, low-cardinality, always used together) behind one FK, rather
  than four separate columns on fact_survey_response.
- fact_job_posting_skill is a factless bridge (no measures) resolving
  required_skills_normalized's multi-valued pipe-delimited tags into a
  proper many-to-many join against dim_skill.
- fact_layoff_event uses dim_date twice as a role-playing dimension
  (date_key for the layoff date, date_added_key for when Layoffs.fyi
  recorded it) - same table, two FK roles.
"""

from dataclasses import dataclass


@dataclass
class DimTable:
    name: str
    columns: list[str]


@dataclass
class FactTable:
    name: str
    columns: list[str]
    foreign_keys: list[str]


# --- Dimension tables (7) ---------------------------------------------------

DIM_DATE = DimTable(
    name="dim_date",
    columns=["date_key", "full_date", "year", "quarter", "month", "month_name", "day"],
)

DIM_COUNTRY = DimTable(
    name="dim_country",
    # continent: enrichment derived from country_converter alongside COUNTRY_MAP,
    # not itself part of COUNTRY_MAP - useful for the layoff trend map tile.
    columns=["country_key", "country_canonical", "continent"],
)

DIM_INDUSTRY = DimTable(
    name="dim_industry",
    columns=["industry_key", "industry_sector"],
)

DIM_ROLE = DimTable(
    name="dim_role",
    # role_source distinguishes job_title (AI Jobs) vs DevType (Survey) -
    # ROLE_MAP's two source vocabularies don't overlap, so this keeps a
    # role_title unambiguous without inventing a shared taxonomy neither
    # dataset actually has. job_category is AI Jobs-only, null for Survey rows.
    columns=["role_key", "role_source", "role_title", "role_category", "job_category"],
)

DIM_COMPANY = DimTable(
    name="dim_company",
    columns=["company_key", "company_name", "stage"],
)

DIM_AI_SENTIMENT = DimTable(
    name="dim_ai_sentiment",
    columns=["ai_sentiment_key", "ai_threat", "ai_select", "ai_sent", "ai_acc"],
)

DIM_SKILL = DimTable(
    name="dim_skill",
    columns=["skill_key", "skill_name"],
)

DIM_TABLES: list[DimTable] = [
    DIM_DATE,
    DIM_COUNTRY,
    DIM_INDUSTRY,
    DIM_ROLE,
    DIM_COMPANY,
    DIM_AI_SENTIMENT,
    DIM_SKILL,
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
        "total_laid_off",
        "percentage_laid_off",
        "funds_raised_usd_millions",
        "source_url",
    ],
    foreign_keys=["date_key", "date_added_key", "company_key", "country_key", "industry_key"],
)

FACT_JOB_POSTING = FactTable(
    name="fact_job_posting",
    columns=[
        "job_posting_key",
        "date_key",
        "role_key",
        "country_key",
        "industry_key",
        "city",
        "company_size",
        "remote_work",
        "is_remote_friendly",
        "is_senior",
        "is_llm_role",
        "education_required",
        "experience_level_canonical",
        "years_of_experience",
        "annual_salary_usd",
        "salary_min_usd",
        "salary_max_usd",
        "salary_tier",
        "ai_salary_premium_pct",
        "demand_score",
        "demand_growth_yoy_pct",
        "benefits_score_10",
    ],
    foreign_keys=["date_key", "role_key", "country_key", "industry_key"],
)

FACT_SURVEY_RESPONSE = FactTable(
    name="fact_survey_response",
    columns=[
        "response_key",
        "role_key",
        "country_key",
        "industry_key",
        "ai_sentiment_key",
        "main_branch",
        "age_bucket",
        "ed_level",
        "employment",
        "remote_work",
        "experience_level_canonical",
        "work_exp",
        "years_code",
        "converted_comp_yearly_winsorized",
        "job_sat",
        "ai_open_topic_id",
        "ai_open_topic_label",
    ],
    foreign_keys=["role_key", "country_key", "industry_key", "ai_sentiment_key"],
)

# Factless bridge: no measures, resolves required_skills_normalized's
# multi-valued tags into one row per (job_posting, skill) pair.
FACT_JOB_POSTING_SKILL = FactTable(
    name="fact_job_posting_skill",
    columns=["job_posting_key", "skill_key"],
    foreign_keys=["job_posting_key", "skill_key"],
)

FACT_TABLES: list[FactTable] = [
    FACT_LAYOFF_EVENT,
    FACT_JOB_POSTING,
    FACT_SURVEY_RESPONSE,
    FACT_JOB_POSTING_SKILL,
]
