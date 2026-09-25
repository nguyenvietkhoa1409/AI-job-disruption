-- 8 dimension tables. Must stay in sync with DIM_TABLES in
-- src/schema/star_schema.py (tests/test_star_schema.py checks this).
-- Every constraint below was verified against the real processed data
-- (layoffs 4,582 / ai_jobs 1,500 / survey 49,078 rows) on Postgres 16.

-- date_key is a YYYYMMDD smart key: loaders compute it directly instead of
-- looking it up. AI Jobs only has posting_year/posting_month, so postings map
-- to the 1st of their month (YYYYMM01).
CREATE TABLE IF NOT EXISTS dim_date (
    date_key   INT PRIMARY KEY,
    full_date  DATE NOT NULL UNIQUE,
    year       SMALLINT NOT NULL,
    quarter    SMALLINT NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    month      SMALLINT NOT NULL CHECK (month BETWEEN 1 AND 12),
    month_name TEXT NOT NULL,
    day        SMALLINT NOT NULL CHECK (day BETWEEN 1 AND 31),
    CHECK (date_key = year * 10000 + month * 100 + day)
);

-- Pre-seeded, gap-free calendar: loaders never insert dates, and BI tools'
-- time intelligence (e.g. Power BI "mark as date table") needs a contiguous
-- date table. Data today spans 2020-03-11 .. 2026-09-09; extend the upper
-- bound here if data ever goes past 2030.
INSERT INTO dim_date
SELECT to_char(d, 'YYYYMMDD')::int, d,
       EXTRACT(year FROM d), EXTRACT(quarter FROM d), EXTRACT(month FROM d),
       trim(to_char(d, 'Month')), EXTRACT(day FROM d)
FROM generate_series(DATE '2020-01-01', DATE '2030-12-31', INTERVAL '1 day') AS g(d)
ON CONFLICT DO NOTHING;

-- 175 values across the 3 datasets, including 'Multi-region / Remote'
-- (AI Jobs "Global" + Survey "Nomadic", see dimension_maps.py).
CREATE TABLE IF NOT EXISTS dim_country (
    country_key       SERIAL PRIMARY KEY,
    country_canonical TEXT NOT NULL UNIQUE,
    continent         TEXT
);

-- 12 sectors from INDUSTRY_MAP.
CREATE TABLE IF NOT EXISTS dim_industry (
    industry_key    SERIAL PRIMARY KEY,
    industry_sector TEXT NOT NULL UNIQUE
);

-- Grain: one row per role identity (57 = 25 AI Jobs job_title + 32 Survey
-- DevType; the two vocabularies do not overlap). job_category and
-- is_llm_role are constant per job_title (verified 25/25), so they are role
-- attributes, not per-posting facts. Survey rows have neither.
CREATE TABLE IF NOT EXISTS dim_role (
    role_key      SERIAL PRIMARY KEY,
    role_source   TEXT NOT NULL CHECK (role_source IN ('job_title', 'DevType')),
    role_title    TEXT NOT NULL,
    role_category TEXT NOT NULL CHECK (role_category IN ('Emerging', 'Traditional')),
    job_category  TEXT,
    is_llm_role   BOOLEAN,
    UNIQUE (role_source, role_title),
    CHECK ( (role_source = 'job_title' AND job_category IS NOT NULL AND is_llm_role IS NOT NULL)
         OR (role_source = 'DevType'   AND job_category IS NULL     AND is_llm_role IS NULL) )
);

-- Grain: one row per company identity. Funding stage is NOT here: 161 of
-- 2,984 companies change stage between layoff events (e.g. Airbnb Private
-- Equity in 2020 -> Post-IPO in 2023), so stage lives on fact_layoff_event.
CREATE TABLE IF NOT EXISTS dim_company (
    company_key  SERIAL PRIMARY KEY,
    company_name TEXT NOT NULL UNIQUE
);

-- Junk dimension: the 4 AI-sentiment answers are low-cardinality and always
-- analysed together (641 distinct combinations in 49,078 responses).
-- NOT NULL because SurveyTransformer fills blanks with 'Not answered'; it
-- also matters for UNIQUE, which would treat NULLs as distinct.
CREATE TABLE IF NOT EXISTS dim_ai_sentiment (
    ai_sentiment_key SERIAL PRIMARY KEY,
    ai_threat        TEXT NOT NULL,
    ai_select        TEXT NOT NULL,
    ai_sent          TEXT NOT NULL,
    ai_acc           TEXT NOT NULL,
    UNIQUE (ai_threat, ai_select, ai_sent, ai_acc)
);

-- 91 normalized skills (required_skills_normalized, SKILL_MAP).
CREATE TABLE IF NOT EXISTS dim_skill (
    skill_key  SERIAL PRIMARY KEY,
    skill_name TEXT NOT NULL UNIQUE
);

-- AI-opinion topics from SurveyFeatureEngineer (NMF on AIOpen), one row per
-- topic per model version. Each topic's label is stored ONCE here, with the
-- top terms that justify it, instead of being repeated on 15,698 fact rows.
-- model_version separates refits (e.g. a new survey wave): a refit can
-- reorder or restructure topics, so labels are only meaningful per version.
-- Labels are matched to topics by content (anchor terms) in the pipeline,
-- which stops if a refit no longer matches the labelled topics.
CREATE TABLE IF NOT EXISTS dim_ai_open_topic (
    ai_open_topic_key SERIAL PRIMARY KEY,
    model_version     TEXT NOT NULL,
    component_id      SMALLINT NOT NULL CHECK (component_id >= 0),
    topic_label       TEXT NOT NULL,
    top_terms         TEXT NOT NULL,
    UNIQUE (model_version, component_id),
    UNIQUE (model_version, topic_label)
);
