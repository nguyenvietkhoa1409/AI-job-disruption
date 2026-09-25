-- Pre-aggregated layoffs by country x month, feeding the dashboard's
-- layoff trend map tile. Uses the layoff date (date_key), not date_added.
-- LEFT JOIN on dim_country so the 2 events with no country are kept as
-- '(Unknown)' instead of silently disappearing from the totals.
CREATE MATERIALIZED VIEW IF NOT EXISTS mart_country_month AS
SELECT
    COALESCE(c.country_canonical, '(Unknown)') AS country_canonical,
    d.year,
    d.month,
    COUNT(*)                   AS layoff_events,
    SUM(f.total_laid_off)      AS total_laid_off,
    AVG(f.percentage_laid_off) AS avg_percentage_laid_off
FROM fact_layoff_event f
JOIN dim_date d         ON d.date_key = f.date_key
LEFT JOIN dim_country c ON c.country_key = f.country_key
GROUP BY 1, d.year, d.month;

-- Required for REFRESH ... CONCURRENTLY.
CREATE UNIQUE INDEX IF NOT EXISTS mart_country_month_pk
    ON mart_country_month (country_canonical, year, month);

-- Re-run after each data load:
--   REFRESH MATERIALIZED VIEW CONCURRENTLY mart_country_month;
