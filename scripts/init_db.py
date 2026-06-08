#!/usr/bin/env python
"""
MandiSense AI — Database Initialization & Schema Bootstrapping Script.
Safe, idempotent, and production-ready.
"""

import os
import sys
from pathlib import Path
import psycopg2

# Resolve paths
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
SCHEMA_PATH = ROOT_DIR / "mandisense_ai" / "db" / "schema.sql"

REQUIRED_TABLES = {
    "prediction_log",
    "market_prices",
    "arrival_volumes",
    "model_registry",
    "api_request_log"
}

def get_db_url() -> str:
    """Retrieve database URL from environment with fallback logic."""
    url = os.environ.get("DATABASE_URL")
    if not url:
        env = os.environ.get("APP__ENVIRONMENT", "development").lower()
        if env == "production":
            print("[CRITICAL] DATABASE_URL environment variable is required in production.", file=sys.stderr)
            sys.exit(1)
        url = "postgresql://user:pass@localhost:5432/mandisense"
        print(f"[INFO] DATABASE_URL missing. Using development fallback: {url}")
    
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url

def init_database():
    """Execute schema script and verify database state."""
    db_url = get_db_url()
    
    print("[INFO] Attempting to connect to database...")
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
    except Exception as e:
        print(f"[CRITICAL] Failed to connect to database: {e}", file=sys.stderr)
        sys.exit(1)
        
    try:
        # 1. Execute schema.sql
        if not SCHEMA_PATH.exists():
            print(f"[CRITICAL] Schema file not found at {SCHEMA_PATH}", file=sys.stderr)
            sys.exit(1)
            
        print(f"[INFO] Reading schema definition from {SCHEMA_PATH.name}...")
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_sql = f.read()
            
        print("[INFO] Executing schema SQL...")
        with conn.cursor() as cur:
            cur.execute(schema_sql)
        print("[INFO] Schema SQL executed successfully.")
        
        # 2. Verify tables exist
        print("[INFO] Verifying created tables...")
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';"
            )
            existing_tables = {row[0] for row in cur.fetchall()}
            
        missing_tables = REQUIRED_TABLES - existing_tables
        if missing_tables:
            print(f"[CRITICAL] Verification failed. Missing tables: {missing_tables}", file=sys.stderr)
            sys.exit(1)
            
        print("[INFO] Database verification complete. All tables exist:")
        for table in sorted(REQUIRED_TABLES):
            print(f"  - public.{table} [OK]")
            
        print("[INFO] Database is operational.")
        
    except Exception as e:
        print(f"[CRITICAL] Database bootstrapping failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    init_database()
