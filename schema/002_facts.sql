-- 4 fact tables. Must stay in sync with FACT_TABLES in
-- src/schema/star_schema.py (tests/test_star_schema.py checks this).
-- Requires 001_dimensions.sql first (FK targets).
--
-- Constraint policy:
--   * Every fact has a natural key (UNIQUE) so the loader can re-run with
--     ON CONFLICT DO NOTHING without duplicating rows.
--   * CHECK what the project itself defines (canonical buckets, numeric
--     ranges, consistency of derived columns). Do NOT check source
--     vocabularies (age buckets, company_size, AI answer wording...) so a
--     future survey wave with reworded options still loads.
--   * NOT NULL only where the real data guarantees it.

-- Grain: one layoff event. Natural key = the (company, date, location) key
-- LayoffsQualityRules deduplicates on (0 duplicates in 4,582 rows; dropping
-- location would leave 5 collisions, e.g. Amazon, same day, 2 cities).
-- dim_date plays two roles: date_key = layoff date, date_added_key = when
-- layoffs.fyi recorded it (they differ in 76% of rows). No CHECK that
-- date_added >= date: 35 events were recorded before their layoff date.
CREATE TABLE IF NOT EXISTS fact_layoff_event (
    layoff_event_key          SERIAL PRIMARY KEY,
    date_key                  INT NOT NULL REFERENCES dim_date (date_key),
    date_added_key             INT NOT NULL REFERENCES dim_date (date_key),
    company_key               INT NOT NULL REFERENCES dim_company (company_key),
    country_key                INT REFERENCES dim_country (country_key),
    industry_key               INT REFERENCES dim_industry (industry_key),
    location                  TEXT NOT NULL,
    stage                     TEXT NOT NULL,
    total_laid_off            INT CHECK (total_laid_off >= 0),
    percentage_laid_off       NUMERIC CHECK (percentage_laid_off BETWEEN 0 AND 1),
    funds_raised_usd_millions NUMERIC CHECK (funds_raised_usd_millions >= 0),
    source_url                TEXT,
    UNIQUE (company_key, date_key, location)
);

-- Grain: one job posting. AI Jobs has 0% missing, hence NOT NULL throughout.
-- is_senior / is_remote_friendly / salary_tier are derivable from other
-- columns (verified 100%); kept for BI convenience, with CHECKs so a
-- drifting transformer fails loudly instead of storing contradictions.
-- annual_salary_usd > salary_max_usd in 288 rows is known synthetic noise
-- (decision #8) and deliberately not constrained.
CREATE TABLE IF NOT EXISTS fact_job_posting (
    job_posting_key            SERIAL PRIMARY KEY,
    job_id                     TEXT NOT NULL UNIQUE,
    date_key                   INT NOT NULL REFERENCES dim_date (date_key),
    role_key                   INT NOT NULL REFERENCES dim_role (role_key),
    country_key                INT NOT NULL REFERENCES dim_country (country_key),
    industry_key                INT NOT NULL REFERENCES dim_industry (industry_key),
    city                       TEXT NOT NULL,
    company_size               TEXT NOT NULL,
    remote_work                TEXT NOT NULL,
    education_required          TEXT NOT NULL,
    experience_level_canonical  TEXT NOT NULL
        CHECK (experience_level_canonical IN ('Entry', 'Mid', 'Senior', 'Lead')),
    years_of_experience         SMALLINT NOT NULL CHECK (years_of_experience >= 0),
    annual_salary_usd           NUMERIC NOT NULL CHECK (annual_salary_usd > 0),
    salary_min_usd               NUMERIC NOT NULL,
    salary_max_usd               NUMERIC NOT NULL,
    ai_salary_premium_pct        NUMERIC NOT NULL,
    demand_score                 SMALLINT NOT NULL CHECK (demand_score BETWEEN 0 AND 100),
    demand_growth_yoy_pct         NUMERIC NOT NULL,
    benefits_score_10             NUMERIC NOT NULL CHECK (benefits_score_10 BETWEEN 0 AND 10),
    is_senior                    BOOLEAN NOT NULL,
    is_remote_friendly           BOOLEAN NOT NULL,
    salary_tier                  TEXT NOT NULL,
    CHECK (salary_min_usd <= salary_max_usd),
    CHECK (is_senior = (experience_level_canonical IN ('Senior', 'Lead'))),
    CHECK (is_remote_friendly = (remote_work <> 'On-site')),
    CHECK (salary_tier = CASE
        WHEN annual_salary_usd <= 100000 THEN 'Entry (<$100k)'
        WHEN annual_salary_usd <= 150000 THEN 'Mid ($100-150k)'
        WHEN annual_salary_usd <= 200000 THEN 'Upper-Mid ($150-200k)'
        WHEN annual_salary_usd <= 300000 THEN 'Senior ($200-300k)'
        ELSE 'Elite (>$300k)' END)
);

-- Grain: one respondent in one survey wave. ResponseId restarts at 1 every
-- year, so the natural key is (survey_year, response_id). No date_key: the
-- survey has no per-respondent date; trend over time = group by survey_year.
-- experience_level_canonical is bucketed from work_exp with the same
-- boundaries as EXPERIENCE_BUCKET_BINS; the CHECK keeps SQL and Python in step.
-- ai_open_topic_key: NULL for answers of 4 words or fewer (no topic assigned).
CREATE TABLE IF NOT EXISTS fact_survey_response (
    response_key                     SERIAL PRIMARY KEY,
    survey_year                      SMALLINT NOT NULL,
    response_id                      INT NOT NULL,
    role_key                         INT REFERENCES dim_role (role_key),
    country_key                      INT REFERENCES dim_country (country_key),
    industry_key                      INT REFERENCES dim_industry (industry_key),
    ai_sentiment_key                 INT NOT NULL REFERENCES dim_ai_sentiment (ai_sentiment_key),
    main_branch                      TEXT,
    age_bucket                       TEXT,
    ed_level                         TEXT,
    employment                       TEXT,
    remote_work                      TEXT,
    work_exp                          SMALLINT CHECK (work_exp BETWEEN 0 AND 100),
    years_code                        SMALLINT CHECK (years_code BETWEEN 0 AND 100),
    experience_level_canonical       TEXT
        CHECK (experience_level_canonical IN ('Entry', 'Mid', 'Senior', 'Lead')),
    converted_comp_yearly_winsorized NUMERIC CHECK (converted_comp_yearly_winsorized > 0),
    job_sat                           SMALLINT CHECK (job_sat BETWEEN 0 AND 10),
    ai_open_topic_key                 INT REFERENCES dim_ai_open_topic (ai_open_topic_key),
    UNIQUE (survey_year, response_id),
    CHECK (experience_level_canonical IS NOT DISTINCT FROM CASE
        WHEN work_exp IS NULL THEN NULL
        WHEN work_exp <= 2 THEN 'Entry'
        WHEN work_exp <= 5 THEN 'Mid'
        WHEN work_exp <= 9 THEN 'Senior'
        ELSE 'Lead' END)
);

-- Factless bridge: one row per (job posting, skill) pair, 9,419 pairs.
-- Resolves required_skills_normalized's pipe-delimited multi-value field.
CREATE TABLE IF NOT EXISTS fact_job_posting_skill (
    job_posting_key INT NOT NULL REFERENCES fact_job_posting (job_posting_key) ON DELETE CASCADE,
    skill_key       INT NOT NULL REFERENCES dim_skill (skill_key),
    PRIMARY KEY (job_posting_key, skill_key)
);

-- Postgres does not index foreign keys automatically; these keep star joins
-- fast as the facts grow.
CREATE INDEX IF NOT EXISTS ix_fle_date     ON fact_layoff_event (date_key);
CREATE INDEX IF NOT EXISTS ix_fle_country  ON fact_layoff_event (country_key);
CREATE INDEX IF NOT EXISTS ix_fle_industry ON fact_layoff_event (industry_key);
CREATE INDEX IF NOT EXISTS ix_fjp_role     ON fact_job_posting (role_key);
CREATE INDEX IF NOT EXISTS ix_fjp_country  ON fact_job_posting (country_key);
CREATE INDEX IF NOT EXISTS ix_fsr_role     ON fact_survey_response (role_key);
CREATE INDEX IF NOT EXISTS ix_fsr_country  ON fact_survey_response (country_key);
CREATE INDEX IF NOT EXISTS ix_fsr_sent     ON fact_survey_response (ai_sentiment_key);
CREATE INDEX IF NOT EXISTS ix_fsr_topic    ON fact_survey_response (ai_open_topic_key);
CREATE INDEX IF NOT EXISTS ix_fjps_skill   ON fact_job_posting_skill (skill_key);
