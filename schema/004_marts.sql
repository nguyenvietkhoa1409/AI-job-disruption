-- Dashboard 1 / 5 marts. All of them use the fixed comparison window, not the
-- full layoff history: layoffs run 2020-03..2026-09, AI Jobs only covers
-- 2025-01..2026-03 and the survey is a single wave, so only that overlap is
-- comparable across sources. Dashboard 2 uses the unwindowed
-- mart_country_industry_month / vw_layoff_event instead.
--
-- The window is DERIVED from the AI Jobs posting dates (the narrowest source),
-- so it moves with the data instead of hiding hard-coded dates in SQL.
-- Empty fact_job_posting -> NULL window -> the marts come out empty.
--
-- A source with no rows for a sector/country yields NULL (not 0) in these
-- marts, so the BI layer can draw "no data" distinctly from a real zero. The
-- same holds for total_laid_off: events whose headcount was never disclosed
-- sum to NULL, not 0 (events_with_headcount says how many contributed).
-- Rows-with-a-NULL-FK (e.g. the survey's missing Industry) are not in the
-- grid; they would have nowhere to sit.

CREATE OR REPLACE VIEW vw_comparison_window AS
SELECT MIN(d.full_date)                                                AS start_date,
       (date_trunc('month', MAX(d.full_date)) + INTERVAL '1 month - 1 day')::date AS end_date
FROM fact_job_posting p
JOIN dim_date d ON d.date_key = p.date_key;

-- Grain: industry_sector (one row per dim_industry row; 12 sectors).
-- AIThreat rate = Yes / answered, with 'Not answered' excluded from the
-- denominator, and both Ns exposed so the BI tooltip can show them.
CREATE MATERIALIZED VIEW IF NOT EXISTS mart_industry_overview AS
WITH layoffs AS (
    SELECT f.industry_key,
           COUNT(*)                           AS layoff_events,
           SUM(f.total_laid_off)              AS total_laid_off,
           COUNT(f.total_laid_off)            AS events_with_headcount
    FROM fact_layoff_event f
    JOIN dim_date d ON d.date_key = f.date_key
    CROSS JOIN vw_comparison_window w
    WHERE d.full_date BETWEEN w.start_date AND w.end_date
    GROUP BY f.industry_key
), postings AS (
    SELECT industry_key, COUNT(*) AS job_postings
    FROM fact_job_posting
    GROUP BY industry_key
), survey AS (
    SELECT r.industry_key,
           COUNT(*)                                          AS survey_responses,
           COUNT(*) FILTER (WHERE s.ai_threat <> 'Not answered') AS ai_threat_answered_n,
           COUNT(*) FILTER (WHERE s.ai_threat = 'Yes')       AS ai_threat_yes_n
    FROM fact_survey_response r
    JOIN dim_ai_sentiment s ON s.ai_sentiment_key = r.ai_sentiment_key
    GROUP BY r.industry_key
)
SELECT i.industry_sector,
       l.layoff_events,
       l.total_laid_off,
       l.events_with_headcount,
       p.job_postings,
       s.survey_responses,
       s.ai_threat_answered_n,
       s.ai_threat_yes_n,
       s.ai_threat_yes_n::numeric / NULLIF(s.ai_threat_answered_n, 0) AS ai_threat_yes_rate
FROM dim_industry i
LEFT JOIN layoffs  l ON l.industry_key = i.industry_key
LEFT JOIN postings p ON p.industry_key = i.industry_key
LEFT JOIN survey   s ON s.industry_key = i.industry_key;

CREATE UNIQUE INDEX IF NOT EXISTS mart_industry_overview_pk
    ON mart_industry_overview (industry_sector);

-- Grain: country_canonical, restricted to the countries AI Jobs reports
-- (the 14 real countries + 'Multi-region / Remote'). A full ~175-country list
-- would leave the Creation column empty for most rows.
-- median_salary_usd is over AI Jobs posted salary (synthetic, illustrative).
CREATE MATERIALIZED VIEW IF NOT EXISTS mart_country_overview AS
WITH layoffs AS (
    SELECT f.country_key,
           COUNT(*)                           AS layoff_events,
           SUM(f.total_laid_off)              AS total_laid_off,
           COUNT(f.total_laid_off)            AS events_with_headcount
    FROM fact_layoff_event f
    JOIN dim_date d ON d.date_key = f.date_key
    CROSS JOIN vw_comparison_window w
    WHERE d.full_date BETWEEN w.start_date AND w.end_date
    GROUP BY f.country_key
), postings AS (
    SELECT country_key,
           COUNT(*)                                                     AS job_postings,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY annual_salary_usd) AS median_salary_usd
    FROM fact_job_posting
    GROUP BY country_key
), survey AS (
    SELECT r.country_key,
           COUNT(*)                                          AS survey_responses,
           COUNT(*) FILTER (WHERE s.ai_threat <> 'Not answered') AS ai_threat_answered_n,
           COUNT(*) FILTER (WHERE s.ai_threat = 'Yes')       AS ai_threat_yes_n
    FROM fact_survey_response r
    JOIN dim_ai_sentiment s ON s.ai_sentiment_key = r.ai_sentiment_key
    GROUP BY r.country_key
)
SELECT c.country_canonical,
       c.continent,
       l.layoff_events,
       l.total_laid_off,
       l.events_with_headcount,
       p.job_postings,
       p.median_salary_usd,
       s.survey_responses,
       s.ai_threat_answered_n,
       s.ai_threat_yes_n,
       s.ai_threat_yes_n::numeric / NULLIF(s.ai_threat_answered_n, 0) AS ai_threat_yes_rate
FROM dim_country c
JOIN postings p      ON p.country_key = c.country_key
LEFT JOIN layoffs l  ON l.country_key = c.country_key
LEFT JOIN survey s   ON s.country_key = c.country_key;

CREATE UNIQUE INDEX IF NOT EXISTS mart_country_overview_pk
    ON mart_country_overview (country_canonical);

-- Grain: industry_sector, ONLY sectors present in both layoffs (within the
-- window, with a disclosed headcount) and AI Jobs. Government (no layoffs),
-- Real Estate and Transportation (no AI postings) are excluded, and both
-- shares are renormalised over the remaining sectors so they each sum to 1.
-- share_gap_pp > 0: the sector takes a larger slice of layoffs than of AI
-- postings. A composition comparison, NOT a flow of people between sectors:
-- nothing links a layoff to a posting.
CREATE MATERIALIZED VIEW IF NOT EXISTS mart_sector_share_gap AS
WITH layoffs AS (
    SELECT f.industry_key, SUM(f.total_laid_off) AS layoff_headcount
    FROM fact_layoff_event f
    JOIN dim_date d ON d.date_key = f.date_key
    CROSS JOIN vw_comparison_window w
    WHERE d.full_date BETWEEN w.start_date AND w.end_date
    GROUP BY f.industry_key
    HAVING SUM(f.total_laid_off) > 0
), postings AS (
    SELECT industry_key, COUNT(*) AS job_postings
    FROM fact_job_posting
    GROUP BY industry_key
), shared AS (
    SELECT l.industry_key, l.layoff_headcount, p.job_postings
    FROM layoffs l
    JOIN postings p ON p.industry_key = l.industry_key
)
SELECT i.industry_sector,
       s.layoff_headcount,
       s.job_postings,
       s.layoff_headcount::numeric / SUM(s.layoff_headcount) OVER ()  AS layoff_share,
       s.job_postings::numeric     / SUM(s.job_postings) OVER ()      AS posting_share,
       100 * (s.layoff_headcount::numeric / SUM(s.layoff_headcount) OVER ()
            - s.job_postings::numeric     / SUM(s.job_postings) OVER ()) AS share_gap_pp
FROM shared s
JOIN dim_industry i ON i.industry_key = s.industry_key;

CREATE UNIQUE INDEX IF NOT EXISTS mart_sector_share_gap_pk
    ON mart_sector_share_gap (industry_sector);
