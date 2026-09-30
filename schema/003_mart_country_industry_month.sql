-- Pre-aggregated layoffs by country x industry x stage x month, feeding the
-- Dashboard 2 trend line and its page filters. Supersedes mart_country_month,
-- which had no industry/stage (so those filters could not touch the trend) and
-- stored AVG(percentage_laid_off): averaging monthly averages when rolling up
-- to global gives wrong weights. This view stores additive SUMs and COUNTs
-- instead, so any roll-up is exact:
--     mean % laid off = SUM(pct_laid_off_sum) / SUM(pct_laid_off_nonnull_count)
-- Uses the layoff date (date_key), not date_added. LEFT JOINs keep events with
-- no country/industry as '(Unknown)' instead of dropping them from totals.
--
-- total_laid_off is ~35% NULL (only a percentage was disclosed), and the gap is
-- worst for shutdowns. total_laid_off_sum therefore undercounts;
-- events_with_headcount says how many events actually contributed to it.
--
-- NOTE for existing databases: CREATE ... IF NOT EXISTS never alters or drops
-- an old object, so a database built before this file keeps the obsolete
-- mart_country_month until `python setup_database.py --reset` (dev only).
CREATE MATERIALIZED VIEW IF NOT EXISTS mart_country_industry_month AS
SELECT
    COALESCE(c.country_canonical, '(Unknown)')       AS country_canonical,
    COALESCE(i.industry_sector, '(Unknown)')         AS industry_sector,
    f.stage,
    date_trunc('month', d.full_date)::date           AS month_start,
    COUNT(*)                                         AS layoff_events,
    COALESCE(SUM(f.total_laid_off), 0)               AS total_laid_off_sum,
    COUNT(f.total_laid_off)                          AS events_with_headcount,
    COALESCE(SUM(f.percentage_laid_off), 0)          AS pct_laid_off_sum,
    COUNT(f.percentage_laid_off)                     AS pct_laid_off_nonnull_count,
    COUNT(*) FILTER (WHERE f.percentage_laid_off = 1) AS shutdown_events
FROM fact_layoff_event f
JOIN dim_date d          ON d.date_key = f.date_key
LEFT JOIN dim_country c  ON c.country_key = f.country_key
LEFT JOIN dim_industry i ON i.industry_key = f.industry_key
GROUP BY 1, 2, 3, 4;

-- Required for REFRESH ... CONCURRENTLY.
CREATE UNIQUE INDEX IF NOT EXISTS mart_country_industry_month_pk
    ON mart_country_industry_month (country_canonical, industry_sector, stage, month_start);

-- Re-run after each data load (WarehouseLoader does this for every mart):
--   REFRESH MATERIALIZED VIEW CONCURRENTLY mart_country_industry_month;
