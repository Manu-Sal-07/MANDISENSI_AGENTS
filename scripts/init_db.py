#!/usr/bin/env python
"""
MandiSense AI - optional database bootstrap.

The database is an *optional accelerator*: the forecast store, the cognition engine and every farmer and trader answer are served
from artefacts that ship in the image, and `/v1/health` reports a missing database as `not_configured`, not as a fault. So this
script never blocks start-up by default:

* no `DATABASE_URL`                -> skip, exit 0
* database unreachable / bad schema -> warn, exit 0 (the API starts in degraded mode and says so on `/v1/health`)

Set `DB_REQUIRED=1` to restore the strict behaviour (any problem exits 1), for a deployment that really depends on Postgres.
"""

import os
import sys
from pathlib import Path

# Resolve paths
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
SCHEMA_PATH = ROOT_DIR / "mandisense_ai" / "db" / "schema.sql"

REQUIRED_TABLES = {
    "prediction_log",
    "market_prices",
    "arrival_volumes",
    "model_registry",
    "api_request_log",
}


def db_required() -> bool:
    return os.environ.get("DB_REQUIRED", "").strip().lower() in {"1", "true", "yes"}


def get_db_url() -> str | None:
    """The configured database URL, or None when no database is configured."""
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if not url:
        return None
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def _fail(message: str) -> int:
    """Exit code for a database problem: 1 only when the database is required, otherwise a warning and 0."""
    if db_required():
        print(f"[CRITICAL] {message}", file=sys.stderr)
        return 1
    print(f"[WARNING] {message} Continuing without a database (set DB_REQUIRED=1 to make this fatal).", file=sys.stderr)
    return 0


def init_database() -> int:
    """Run the schema script and verify tables. Returns the process exit code."""
    db_url = get_db_url()
    if db_url is None:
        if db_required():
            print("[CRITICAL] DATABASE_URL is required because DB_REQUIRED is set.", file=sys.stderr)
            return 1
        print("[INFO] DATABASE_URL not set: skipping database bootstrap (the app serves from local artefacts).")
        return 0

    print("[INFO] Attempting to connect to database...")
    try:
        import psycopg2  # imported here so a deployment without a database never needs the driver to load

        conn = psycopg2.connect(db_url, connect_timeout=10)
        conn.autocommit = True
    except Exception as exc:  # noqa: BLE001 - any connection failure is handled the same way
        return _fail(f"Failed to connect to database: {exc}.")

    try:
        if not SCHEMA_PATH.exists():
            return _fail(f"Schema file not found at {SCHEMA_PATH}.")

        print(f"[INFO] Reading schema definition from {SCHEMA_PATH.name}...")
        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

        print("[INFO] Executing schema SQL...")
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        print("[INFO] Schema SQL executed successfully.")

        with conn.cursor() as cur:
            cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
            existing_tables = {row[0] for row in cur.fetchall()}

        missing_tables = REQUIRED_TABLES - existing_tables
        if missing_tables:
            return _fail(f"Verification failed. Missing tables: {sorted(missing_tables)}.")

        print("[INFO] Database verification complete. All tables exist:")
        for table in sorted(REQUIRED_TABLES):
            print(f"  - public.{table} [OK]")
        print("[INFO] Database is operational.")
        return 0
    except Exception as exc:  # noqa: BLE001
        return _fail(f"Database bootstrapping failed: {exc}.")
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(init_database())
