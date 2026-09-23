-- Matches src/schema/star_schema.py's FACT_TABLES exactly (4 tables).
-- Requires 001_dimensions.sql applied first (FK targets).

-- dim_date used twice (role-playing dimension): date_key is the layoff
-- date itself, date_added_key is when layoffs.fyi recorded it. Both are
-- rows in the same dim_date table.
CREATE TABLE IF NOT EXISTS fact_layoff_event (
    layoff_event_key           SERIAL PRIMARY KEY,
    date_key                   INT REFERENCES dim_date(date_key),
    date_added_key             INT REFERENCES dim_date(date_key),
    company_key                INT REFERENCES dim_company(company_key),
    country_key                INT REFERENCES dim_country(country_key),
    industry_key                INT REFERENCES dim_industry(industry_key),
    location                    TEXT,
    total_laid_off               NUMERIC,
    percentage_laid_off           NUMERIC CHECK (percentage_laid_off BETWEEN 0 AND 1),
    funds_raised_usd_millions      NUMERIC,
    source_url                     TEXT
);

-- experience_level_canonical is a degenerate attribute here (not a separate
-- dim_experience_level) - dim_role's grain is role identity, which recurs
-- across many experience levels, so experience belongs on the fact.
CREATE TABLE IF NOT EXISTS fact_job_posting (
    job_posting_key             SERIAL PRIMARY KEY,
    date_key                    INT REFERENCES dim_date(date_key),
    role_key                    INT REFERENCES dim_role(role_key),
    country_key                 INT REFERENCES dim_country(country_key),
    industry_key                INT REFERENCES dim_industry(industry_key),
    city                        TEXT,
    company_size                TEXT,
    remote_work                 TEXT,
    is_remote_friendly          BOOLEAN,
    is_senior                   BOOLEAN,
    is_llm_role                 BOOLEAN,
    education_required          TEXT,
    experience_level_canonical  TEXT CHECK (experience_level_canonical IN ('Entry', 'Mid', 'Senior', 'Lead')),
    years_of_experience         NUMERIC,
    annual_salary_usd           NUMERIC,
    salary_min_usd               NUMERIC,
    salary_max_usd               NUMERIC,
    salary_tier                  TEXT,
    ai_salary_premium_pct         NUMERIC,
    demand_score                  INT,
    demand_growth_yoy_pct          NUMERIC,
    benefits_score_10               NUMERIC
);

-- experience_level_canonical bucketed from WorkExp (same Entry/Mid/Senior/
-- Lead boundaries as EXPERIENCE_MAP) so this compares on equal footing with
-- fact_job_posting's version. ai_open_topic_id/label included directly
-- (not gated behind the "does the dashboard need it" open question).
CREATE TABLE IF NOT EXISTS fact_survey_response (
    response_key                     SERIAL PRIMARY KEY,
    role_key                         INT REFERENCES dim_role(role_key),
    country_key                      INT REFERENCES dim_country(country_key),
    industry_key                     INT REFERENCES dim_industry(industry_key),
    ai_sentiment_key                 INT REFERENCES dim_ai_sentiment(ai_sentiment_key),
    main_branch                      TEXT,
    age_bucket                       TEXT,
    ed_level                         TEXT,
    employment                       TEXT,
    remote_work                      TEXT,
    experience_level_canonical       TEXT CHECK (experience_level_canonical IN ('Entry', 'Mid', 'Senior', 'Lead')),
    work_exp                          NUMERIC,
    years_code                        NUMERIC,
    converted_comp_yearly_winsorized   NUMERIC,
    job_sat                             NUMERIC,
    ai_open_topic_id                     INT,
    ai_open_topic_label                   TEXT
);

-- Factless bridge: no measures, one row per (job_posting, skill) pair.
CREATE TABLE IF NOT EXISTS fact_job_posting_skill (
    job_posting_key INT NOT NULL REFERENCES fact_job_posting(job_posting_key),
    skill_key       INT NOT NULL REFERENCES dim_skill(skill_key),
    PRIMARY KEY (job_posting_key, skill_key)
);
