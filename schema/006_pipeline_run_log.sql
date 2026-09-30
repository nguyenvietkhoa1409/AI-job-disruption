-- Operational (not star-schema) table behind Dashboard 6's pipeline-health
-- strip: one row per source per WarehouseLoader.run(), append-only. It is NOT
-- one of the 4 fact / 8 dimension tables, so it is listed in OPS_TABLES in
-- src/schema/star_schema.py and deliberately has no natural key: every run is
-- a new row, and re-running the loader must still add its own history row.
--   rows_clean       rows in data/processed/<source>.csv
--   rows_quarantined rows in data/quarantine/<source>.csv (failed quality rules)
--   rows_inserted    rows actually new in this run's fact table (0 on a repeat)
-- rows ingested = rows_clean + rows_quarantined.
CREATE TABLE IF NOT EXISTS pipeline_run_log (
    run_log_key      SERIAL PRIMARY KEY,
    run_ts           TIMESTAMPTZ NOT NULL DEFAULT now(),
    source           TEXT NOT NULL CHECK (source IN ('layoffs', 'ai_jobs', 'survey')),
    rows_clean       INT NOT NULL CHECK (rows_clean >= 0),
    rows_quarantined INT NOT NULL CHECK (rows_quarantined >= 0),
    rows_inserted    INT NOT NULL CHECK (rows_inserted >= 0)
);
