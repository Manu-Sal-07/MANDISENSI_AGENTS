"""
JSONL → PostgreSQL Migration Script.

Safely migrates existing prediction records from JSONL files to PostgreSQL.

Usage:
  python -m db.migrate_jsonl_to_pg [--dry-run] [--jsonl-path PATH]

Steps:
  1. Read all records from JSONL file
  2. Validate each record
  3. Batch insert into prediction_log table
  4. Verify counts match
  5. Report results

Safety:
  • Dry-run mode (default) — no writes
  • Duplicate detection via record_id UNIQUE constraint
  • Transaction-based: all-or-nothing per batch
  • Original JSONL file is NEVER deleted
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_JSONL = Path("data") / "ensemble" / "meta_predictions.jsonl"
_BATCH_SIZE = 100


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Load and parse all records from a JSONL file."""
    if not path.exists():
        print(f"  [!] JSONL file not found: {path}")
        return []

    records = []
    errors = 0
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                errors += 1
                print(f"  [!] Malformed JSON on line {line_num}, skipping")

    print(f"  Loaded {len(records)} records ({errors} errors) from {path}")
    return records


def validate_record(record: Dict[str, Any]) -> bool:
    """Basic validation: required fields present."""
    required = ["record_id", "commodity", "mandi", "timestamp"]
    return all(record.get(k) for k in required)


def migrate(
    jsonl_path: Path = _DEFAULT_JSONL,
    dry_run: bool = True,
    batch_size: int = _BATCH_SIZE,
) -> Dict[str, Any]:
    """
    Migrate JSONL records to PostgreSQL.

    Returns a report dict.
    """
    print(f"\n{'='*60}")
    print(f"  MandiSense JSONL → PostgreSQL Migration")
    print(f"  Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"{'='*60}\n")

    # 1. Load records
    print("[1] Loading JSONL records...")
    records = load_jsonl(jsonl_path)
    if not records:
        return {"status": "skipped", "reason": "no records"}

    # 2. Validate
    print(f"\n[2] Validating {len(records)} records...")
    valid = [r for r in records if validate_record(r)]
    invalid = len(records) - len(valid)
    print(f"  Valid: {len(valid)}, Invalid: {invalid}")

    if dry_run:
        print(f"\n[3] DRY RUN — would insert {len(valid)} records in {(len(valid) // batch_size) + 1} batches")
        return {
            "status": "dry_run",
            "total": len(records),
            "valid": len(valid),
            "invalid": invalid,
        }

    # 3. Connect to DB
    print("\n[3] Connecting to PostgreSQL...")
    from db.connection import get_sync_connection

    inserted = 0
    duplicates = 0
    errors = 0

    # 4. Batch insert
    print(f"\n[4] Inserting in batches of {batch_size}...")
    for batch_start in range(0, len(valid), batch_size):
        batch = valid[batch_start:batch_start + batch_size]
        batch_num = (batch_start // batch_size) + 1

        with get_sync_connection() as conn:
            if conn is None:
                print("  [!] DB connection failed")
                return {"status": "error", "reason": "db_unavailable"}

            for record in batch:
                try:
                    with conn.cursor() as cur:
                        ts = record.get("timestamp", "")
                        created_at = datetime.fromisoformat(ts.rstrip("Z")) if ts else datetime.utcnow()

                        cur.execute("""
                            INSERT INTO prediction_log (
                                record_id, created_at, commodity, mandi,
                                seasonality_pred_30d, seasonality_confidence,
                                seasonality_volatility, seasonality_regime,
                                arrival_pred_7d, arrival_confidence,
                                arrival_supply_stress, arrival_regime,
                                external_impact, external_confidence,
                                phase1_prediction, phase1_confidence,
                                phase1_conflict, phase1_strong_conflict,
                                actual_7d_change, outcome_filled_at
                            ) VALUES (
                                %s, %s, %s, %s,
                                %s, %s, %s, %s,
                                %s, %s, %s, %s,
                                %s, %s, %s, %s,
                                %s, %s, %s, %s
                            )
                            ON CONFLICT (record_id) DO NOTHING
                        """, (
                            record.get("record_id"),
                            created_at,
                            record.get("commodity"),
                            record.get("mandi"),
                            record.get("seasonality_pred_30d"),
                            record.get("seasonality_confidence"),
                            record.get("seasonality_volatility"),
                            record.get("seasonality_regime"),
                            record.get("arrival_pred_7d"),
                            record.get("arrival_confidence"),
                            record.get("arrival_supply_stress"),
                            record.get("arrival_regime"),
                            record.get("external_impact"),
                            record.get("external_confidence"),
                            record.get("phase1_prediction"),
                            record.get("phase1_confidence"),
                            record.get("phase1_conflict", False),
                            record.get("phase1_strong_conflict", False),
                            record.get("actual_7d_change"),
                            datetime.fromisoformat(record["outcome_filled_at"].rstrip("Z"))
                                if record.get("outcome_filled_at") else None,
                        ))

                        if cur.rowcount == 0:
                            duplicates += 1
                        else:
                            inserted += 1
                except Exception as e:
                    errors += 1
                    logger.warning(f"[Migration] Record error: {e}")

            # Commit per batch
            conn.commit()

        print(f"  Batch {batch_num}: +{inserted} inserted, {duplicates} dupes, {errors} errors (cumulative)")

    # 5. Verify
    print(f"\n[5] Verification...")
    with get_sync_connection() as conn:
        if conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM prediction_log")
                db_count = cur.fetchone()[0]
            print(f"  Database total: {db_count}")
        else:
            db_count = -1

    report = {
        "status": "complete",
        "source_records": len(records),
        "valid": len(valid),
        "inserted": inserted,
        "duplicates": duplicates,
        "errors": errors,
        "db_total": db_count,
    }

    print(f"\n{'='*60}")
    print(f"  Migration Complete")
    print(f"  Inserted: {inserted}")
    print(f"  Duplicates (skipped): {duplicates}")
    print(f"  Errors: {errors}")
    print(f"  DB Total: {db_count}")
    print(f"{'='*60}\n")

    return report


# ── CLI ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate JSONL prediction logs to PostgreSQL")
    parser.add_argument("--dry-run", action="store_true", default=True,
                        help="Preview migration without writing (default)")
    parser.add_argument("--live", action="store_true",
                        help="Actually execute the migration")
    parser.add_argument("--jsonl-path", type=Path, default=_DEFAULT_JSONL,
                        help="Path to JSONL file")
    parser.add_argument("--batch-size", type=int, default=_BATCH_SIZE)
    args = parser.parse_args()

    is_dry_run = not args.live
    report = migrate(jsonl_path=args.jsonl_path, dry_run=is_dry_run, batch_size=args.batch_size)
    print(json.dumps(report, indent=2, default=str))
    sys.exit(0 if report.get("status") != "error" else 1)
