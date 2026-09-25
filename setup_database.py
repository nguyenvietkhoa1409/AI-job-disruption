"""Apply schema/*.sql to the Postgres database described by .env.

Two ways the schema gets into Postgres - pick whichever fits the moment:
- docker compose up -d: the postgres image auto-runs schema/*.sql, but ONLY
  on the very first start (empty pg_data volume).
- python setup_database.py: runs the same files any time, against any
  Postgres on POSTGRES_HOST:POSTGRES_PORT (Docker or a native install).

Default mode is safe to re-run: every statement is IF NOT EXISTS /
ON CONFLICT DO NOTHING. But IF NOT EXISTS never changes a table that already
exists, so after editing an existing table's DDL use:

    python setup_database.py --reset

which drops every table, view and row in the public schema and rebuilds it
from schema/*.sql. Development only: all loaded data is lost (re-run the
loader afterwards).
"""

import argparse
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

SCHEMA_DIR = Path(__file__).resolve().parent / "schema"


def _connect():
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--reset", action="store_true", help="drop the public schema and rebuild it (loses all data)")
    args = parser.parse_args()

    load_dotenv()
    try:
        conn = _connect()
    except KeyError as exc:
        print(f"[FAIL] missing {exc} - copy .env.example to .env and fill it in")
        return 1
    except psycopg2.OperationalError as exc:
        print(f"[FAIL] could not connect: {exc}")
        print("       is `docker compose up -d` running?")
        return 1

    sql_files = sorted(SCHEMA_DIR.glob("*.sql"))
    if not sql_files:
        print(f"[FAIL] no .sql files found in {SCHEMA_DIR}")
        return 1

    try:
        # One transaction: either every file applies, or nothing changes.
        with conn:
            with conn.cursor() as cur:
                if args.reset:
                    print("[..]   --reset: dropping and recreating schema public")
                    cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
                for path in sql_files:
                    print(f"[..]   applying {path.name}")
                    cur.execute(path.read_text(encoding="utf-8"))

                cur.execute(
                    "SELECT count(*) FILTER (WHERE table_name LIKE 'dim\\_%'),"
                    "       count(*) FILTER (WHERE table_name LIKE 'fact\\_%')"
                    " FROM information_schema.tables"
                    " WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
                )
                n_dim, n_fact = cur.fetchone()
                cur.execute("SELECT count(*) FROM pg_matviews WHERE schemaname = 'public'")
                (n_mart,) = cur.fetchone()
    except psycopg2.Error as exc:
        print(f"[FAIL] {exc}")
        return 1
    finally:
        conn.close()

    print(f"\nsetup_database: applied {len(sql_files)} file(s) - "
          f"{n_dim} dimension, {n_fact} fact tables, {n_mart} materialized view(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
