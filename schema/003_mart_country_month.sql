-- Rewritten for fact_layoff_event + dim_date's year/month columns
-- (previous version assumed a single "month" DATE column that no longer
-- exists in the merged star_schema.py design).
CREATE MATERIALIZED VIEW IF NOT EXISTS mart_country_month AS
SELECT
    c.country_canonical,
    d.year,
    d.month,
    COUNT(*)                   AS layoff_events,
    SUM(f.total_laid_off)      AS total_laid_off,
    AVG(f.percentage_laid_off) AS avg_percentage_laid_off
FROM fact_layoff_event f
JOIN dim_country c ON c.country_key = f.country_key
JOIN dim_date d     ON d.date_key = f.date_key   -- the layoff date, not date_added
GROUP BY c.country_canonical, d.year, d.month;

CREATE UNIQUE INDEX IF NOT EXISTS mart_country_month_pk
    ON mart_country_month (country_canonical, year, month);

-- Re-run after each data load to refresh:
--   REFRESH MATERIALIZED VIEW CONCURRENTLY mart_country_month;
