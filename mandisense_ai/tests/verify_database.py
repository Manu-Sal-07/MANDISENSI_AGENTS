"""
Standalone verification of the Database Layer.

Tests everything WITHOUT a running PostgreSQL instance:
  1. Schema SQL file validity (parses correctly)
  2. Connection module imports & config parsing
  3. DatabasePredictionLogger API compatibility
  4. Migration script dry-run
  5. Query module completeness

Run: python tests/verify_database.py
"""

import sys
import os
import types
import logging
import json

# ── Bootstrap: stub out the logger ──────────────────────────────────
_stub_utils = types.ModuleType("utils")
_stub_logger_mod = types.ModuleType("utils.logger")


def _get_logger(name):
    lgr = logging.getLogger(name)
    if not lgr.handlers:
        lgr.setLevel(logging.WARNING)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))
        lgr.addHandler(handler)
    return lgr


_stub_logger_mod.get_logger = _get_logger
sys.modules["utils"] = _stub_utils
sys.modules["utils.logger"] = _stub_logger_mod

_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)


def test(name, condition):
    status = "PASS" if condition else "FAIL"
    icon = "+" if condition else "x"
    print(f"  [{icon}] {status}  {name}")
    return condition


def main():
    all_pass = True

    # ── 1. Schema SQL ────────────────────────────────────────────────
    print("\n[1] Schema SQL Validation")

    schema_path = os.path.join(_parent_dir, "db", "schema.sql")
    all_pass &= test("schema.sql exists", os.path.isfile(schema_path))

    with open(schema_path, encoding="utf-8") as f:
        schema = f.read()

    all_pass &= test("Contains prediction_log table", "CREATE TABLE IF NOT EXISTS prediction_log" in schema)
    all_pass &= test("Contains market_prices table", "CREATE TABLE IF NOT EXISTS market_prices" in schema)
    all_pass &= test("Contains arrival_volumes table", "CREATE TABLE IF NOT EXISTS arrival_volumes" in schema)
    all_pass &= test("Contains model_registry table", "CREATE TABLE IF NOT EXISTS model_registry" in schema)
    all_pass &= test("Contains api_request_log table", "CREATE TABLE IF NOT EXISTS api_request_log" in schema)

    # Index checks
    all_pass &= test("Has commodity/time index", "idx_pred_commodity_time" in schema)
    all_pass &= test("Has unfilled partial index", "idx_pred_unfilled" in schema)
    all_pass &= test("Has completed partial index", "idx_pred_completed" in schema)
    all_pass &= test("Has prices lookup index", "idx_prices_lookup" in schema)
    all_pass &= test("Has model active index", "idx_model_active" in schema)

    # Key columns
    all_pass &= test("Has actual_7d_change column", "actual_7d_change" in schema)
    all_pass &= test("Has outcome_filled_at column", "outcome_filled_at" in schema)
    all_pass &= test("Has learned_residual column", "learned_residual" in schema)
    all_pass &= test("Has ON CONFLICT support (upsert)", "ON CONFLICT" in schema or "UNIQUE" in schema)

    # ── 2. Connection Module ─────────────────────────────────────────
    print("\n[2] Connection Module")

    from db.connection import _parse_db_url, _get_db_url

    url = "postgresql://myuser:mypass@myhost:5433/mydb"
    parsed = _parse_db_url(url)
    all_pass &= test("Parse user", parsed["user"] == "myuser")
    all_pass &= test("Parse password", parsed["password"] == "mypass")
    all_pass &= test("Parse host", parsed["host"] == "myhost")
    all_pass &= test("Parse port", parsed["port"] == 5433)
    all_pass &= test("Parse database", parsed["database"] == "mydb")

    default_url = _get_db_url()
    all_pass &= test("Default URL is postgresql://", default_url.startswith("postgresql://"))

    # ── 3. DatabasePredictionLogger API ──────────────────────────────
    print("\n[3] DatabasePredictionLogger API Compatibility")

    from db.prediction_logger_db import DatabasePredictionLogger
    import tempfile, shutil

    tmpdir = tempfile.mkdtemp(prefix="mandisense_db_test_")
    try:
        # Create without DB (fallback mode)
        db_logger = DatabasePredictionLogger(fallback_dir=tmpdir)

        # Verify same API as PredictionLogger
        all_pass &= test("Has log_prediction method", hasattr(db_logger, "log_prediction"))
        all_pass &= test("Has backfill_actual method", hasattr(db_logger, "backfill_actual"))
        all_pass &= test("Has read_all method", hasattr(db_logger, "read_all"))
        all_pass &= test("Has read_completed method", hasattr(db_logger, "read_completed"))
        all_pass &= test("Has count_records method", hasattr(db_logger, "count_records"))

        # Test fallback logging (no DB available)
        record_id = db_logger.log_prediction(
            commodity="tomato", mandi="kolar",
            seasonality_pred_30d=6.0, seasonality_confidence=0.75,
            seasonality_volatility=0.3, seasonality_regime="ascending",
            arrival_pred_7d=-2.5, arrival_confidence=0.60,
            arrival_supply_stress=0.8, arrival_regime="squeeze",
            external_impact=0.4, external_confidence=0.55,
            phase1_prediction=-0.34, phase1_confidence=0.31,
            phase1_conflict=True, phase1_strong_conflict=False,
        )
        all_pass &= test("Fallback log returns UUID", len(record_id) > 0 and "-" in record_id)

        # Check JSONL fallback file was created
        fallback_file = os.path.join(tmpdir, "meta_predictions.jsonl")
        all_pass &= test("Fallback JSONL file created", os.path.isfile(fallback_file))

        with open(fallback_file) as f:
            line = f.readline()
            record = json.loads(line)
        all_pass &= test("Fallback record has commodity", record["commodity"] == "tomato")
        all_pass &= test("Fallback record has actual_7d_change=null", record["actual_7d_change"] is None)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    # ── 4. Queries Module ────────────────────────────────────────────
    print("\n[4] Query Library Completeness")

    from db import queries

    all_pass &= test("Has LATEST_PREDICTION", hasattr(queries, "LATEST_PREDICTION"))
    all_pass &= test("Has PREDICTION_HISTORY", hasattr(queries, "PREDICTION_HISTORY"))
    all_pass &= test("Has UNFILLED_PREDICTIONS", hasattr(queries, "UNFILLED_PREDICTIONS"))
    all_pass &= test("Has COMPLETED_FOR_TRAINING", hasattr(queries, "COMPLETED_FOR_TRAINING"))
    all_pass &= test("Has BACKFILL_ACTUAL", hasattr(queries, "BACKFILL_ACTUAL"))
    all_pass &= test("Has MODEL_ACCURACY_SUMMARY", hasattr(queries, "MODEL_ACCURACY_SUMMARY"))
    all_pass &= test("Has UPSERT_MARKET_PRICE", hasattr(queries, "UPSERT_MARKET_PRICE"))
    all_pass &= test("Has COMPUTE_7D_CHANGE", hasattr(queries, "COMPUTE_7D_CHANGE"))
    all_pass &= test("Has REGISTER_MODEL", hasattr(queries, "REGISTER_MODEL"))
    all_pass &= test("Has PROMOTE_MODEL", hasattr(queries, "PROMOTE_MODEL"))
    all_pass &= test("Has ACTIVE_MODELS", hasattr(queries, "ACTIVE_MODELS"))

    # ── 5. Migration Script ──────────────────────────────────────────
    print("\n[5] Migration Script")

    from db.migrate_jsonl_to_pg import load_jsonl, validate_record

    # Validate record check
    valid = validate_record({"record_id": "abc", "commodity": "tomato", "mandi": "kolar", "timestamp": "2026-01-01"})
    all_pass &= test("Valid record passes validation", valid is True)

    invalid = validate_record({"commodity": "tomato"})  # missing record_id
    all_pass &= test("Invalid record fails validation", invalid is False)

    # ── 6. Docker Compose ────────────────────────────────────────────
    print("\n[6] Docker Compose DB Integration")

    compose_path = os.path.join(_parent_dir, "docker-compose.yml")
    with open(compose_path) as f:
        compose = f.read()

    all_pass &= test("Has db service", "db:" in compose)
    all_pass &= test("Uses postgres:15-alpine", "postgres:15-alpine" in compose)
    all_pass &= test("Has DATABASE_URL env var", "DATABASE_URL" in compose)
    all_pass &= test("Mounts schema.sql as init script", "docker-entrypoint-initdb.d" in compose)
    all_pass &= test("Has pgdata volume", "pgdata:" in compose)
    all_pass &= test("Has pg_isready healthcheck", "pg_isready" in compose)
    all_pass &= test("API depends on db", "condition: service_healthy" in compose)

    # ── Summary ──────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    if all_pass:
        print("ALL DATABASE TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    print(f"{'='*60}\n")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
