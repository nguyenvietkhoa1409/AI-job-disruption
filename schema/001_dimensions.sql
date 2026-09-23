-- Matches src/schema/star_schema.py's DIM_TABLES exactly (7 tables).
-- UNIQUE constraints and CHECKs below are this file's own addition on top
-- of that module (dataclasses describe columns, not SQL-level constraints) -
-- needed so a loader can look up "does this dimension row already exist"
-- before inserting.

CREATE TABLE IF NOT EXISTS dim_date (
    date_key   SERIAL PRIMARY KEY,
    full_date  DATE NOT NULL UNIQUE,
    year       INT NOT NULL,
    quarter    INT NOT NULL,
    month      INT NOT NULL,
    month_name TEXT NOT NULL,
    day        INT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_country (
    country_key       SERIAL PRIMARY KEY,
    country_canonical TEXT NOT NULL UNIQUE,
    continent         TEXT
);

CREATE TABLE IF NOT EXISTS dim_industry (
    industry_key    SERIAL PRIMARY KEY,
    industry_sector TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS dim_role (
    role_key      SERIAL PRIMARY KEY,
    role_source   TEXT NOT NULL CHECK (role_source IN ('job_title', 'DevType')),
    role_title    TEXT NOT NULL,
    role_category TEXT NOT NULL CHECK (role_category IN ('Emerging', 'Traditional')),
    job_category  TEXT,  -- AI Jobs only, NULL for Survey-sourced rows
    UNIQUE (role_source, role_title)
);

CREATE TABLE IF NOT EXISTS dim_company (
    company_key  SERIAL PRIMARY KEY,
    company_name TEXT NOT NULL UNIQUE,
    stage        TEXT  -- funding stage folded in here, not a separate dim
);

-- Junk dimension: bundles the 4 correlated, always-used-together AI
-- sentiment fields behind one FK instead of 4 separate fact columns.
CREATE TABLE IF NOT EXISTS dim_ai_sentiment (
    ai_sentiment_key SERIAL PRIMARY KEY,
    ai_threat        TEXT,
    ai_select        TEXT,
    ai_sent          TEXT,
    ai_acc           TEXT,
    UNIQUE (ai_threat, ai_select, ai_sent, ai_acc)
);

CREATE TABLE IF NOT EXISTS dim_skill (
    skill_key  SERIAL PRIMARY KEY,
    skill_name TEXT NOT NULL UNIQUE
);
