"""
Standalone verification of the Production System Architecture.

Tests the production infrastructure WITHOUT requiring running services
(Redis, PostgreSQL, etc). Validates:
  1. API app creation and route registration
  2. Pydantic schema validation
  3. Orchestrator construction
  4. Retraining pipeline (offline mode)
  5. Docker & Nginx config file existence

Run: python tests/verify_production.py
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
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.WARNING)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s | %(name)s | %(message)s"))
        logger.addHandler(handler)
    return logger


_stub_logger_mod.get_logger = _get_logger
sys.modules["utils"] = _stub_utils
sys.modules["utils.logger"] = _stub_logger_mod

# Set up import path
_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)


# ── Test framework ──────────────────────────────────────────────────

def test(name, condition):
    status = "PASS" if condition else "FAIL"
    icon = "+" if condition else "x"
    print(f"  [{icon}] {status}  {name}")
    return condition


def main():
    all_pass = True

    # ── 1. Pydantic Schemas ─────────────────────────────────────────
    print("\n[1] API Schemas")

    from api.schemas.models import (
        PredictRequest, PredictResponse, HistoryResponse,
        ModelStatusResponse, HealthResponse, PredictionDetail,
        Attribution, RiskFlags, Phase2Info, ResponseMetadata
    )

    # Valid request
    req = PredictRequest(commodity="Tomato", mandi="  Kolar  ")
    all_pass &= test("PredictRequest normalizes to lowercase", req.commodity == "tomato" and req.mandi == "kolar")
    all_pass &= test("PredictRequest defaults use_learned=True", req.use_learned is True)

    # Validation: empty commodity
    try:
        PredictRequest(commodity="", mandi="kolar")
        all_pass &= test("Empty commodity rejected", False)
    except Exception:
        all_pass &= test("Empty commodity rejected", True)

    # Response construction
    resp = PredictResponse(
        request_id="req_test123",
        commodity="tomato",
        mandi="kolar",
        prediction=PredictionDetail(price_change_7d_pct=-0.41, confidence=0.27, direction="bearish"),
        attribution=Attribution(seasonality_pct=28.5, arrival_pct=52.1, external_pct=19.4),
        risk_flags=RiskFlags(conflict_detected=True, low_confidence=True),
        phase2_info=Phase2Info(mode="blended", alpha=0.6, regime_detected="supply_shock"),
        metadata=ResponseMetadata(generated_at="2026-04-26T18:00:00Z", latency_ms=142.3),
    )
    all_pass &= test("PredictResponse serializes to dict", isinstance(resp.model_dump(), dict))
    all_pass &= test("Response has all fields", resp.prediction.direction == "bearish")

    # HealthResponse
    health = HealthResponse(status="healthy", uptime_seconds=100.0, components={"cache": "ok"})
    all_pass &= test("HealthResponse construction", health.status == "healthy")

    # ── 2. FastAPI App ──────────────────────────────────────────────
    print("\n[2] FastAPI Application")

    from api.app import create_app
    app = create_app()

    route_paths = [r.path for r in app.routes if hasattr(r, "path")]
    all_pass &= test("/v1/predict registered", "/v1/predict" in route_paths)
    all_pass &= test("/v1/prediction/history registered", "/v1/prediction/history" in route_paths)
    all_pass &= test("/v1/model/status registered", "/v1/model/status" in route_paths)
    all_pass &= test("/v1/health registered", "/v1/health" in route_paths)
    all_pass &= test("/docs registered", "/docs" in route_paths)
    all_pass &= test("App title is MandiSense AI", app.title == "MandiSense AI")
    all_pass &= test("App version is 2.5.0", app.version == "2.5.0")

    # ── 3. Orchestrator ─────────────────────────────────────────────
    print("\n[3] PredictionController")

    from orchestrator.prediction_controller import PredictionController
    ctrl = PredictionController(redis_client=None)
    all_pass &= test("Controller created without Redis", ctrl.redis is None)
    all_pass &= test("PredictionLogger loaded", ctrl._prediction_logger is not None)

    # ── 4. Retraining Pipeline ──────────────────────────────────────
    print("\n[4] Retraining Pipeline")

    from tasks.retraining import run_retraining
    # Should return "skipped" since there's no completed prediction data
    report = run_retraining()
    all_pass &= test(f"Retraining handles no data gracefully (status={report.get('status')})",
                     report.get("status") == "skipped")

    # ── 5. Backfill Pipeline ────────────────────────────────────────
    print("\n[5] Backfill Pipeline")

    from tasks.backfill import run_backfill, _is_older_than
    from datetime import datetime

    all_pass &= test("_is_older_than detects old timestamps",
                     _is_older_than("2020-01-01T00:00:00Z", 7, datetime(2020, 2, 1)))
    all_pass &= test("_is_older_than rejects recent timestamps",
                     not _is_older_than("2020-01-30T00:00:00Z", 7, datetime(2020, 2, 1)))

    result = run_backfill()
    all_pass &= test(f"Backfill handles no records gracefully (updated={result.get('updated')})",
                     result.get("updated") == 0)

    # ── 6. Infrastructure Files ─────────────────────────────────────
    print("\n[6] Infrastructure Files")

    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    all_pass &= test("Dockerfile exists", os.path.isfile(os.path.join(base, "Dockerfile")))
    all_pass &= test("docker-compose.yml exists", os.path.isfile(os.path.join(base, "docker-compose.yml")))
    all_pass &= test("nginx.conf exists", os.path.isfile(os.path.join(base, "nginx.conf")))

    # Verify docker-compose has required services
    with open(os.path.join(base, "docker-compose.yml")) as f:
        compose = f.read()
    all_pass &= test("docker-compose has api service", "api:" in compose)
    all_pass &= test("docker-compose has redis service", "redis:" in compose)
    all_pass &= test("docker-compose has nginx service", "nginx:" in compose)

    # Verify nginx has rate limiting
    with open(os.path.join(base, "nginx.conf")) as f:
        nginx = f.read()
    all_pass &= test("nginx has rate limiting", "limit_req_zone" in nginx)
    all_pass &= test("nginx has upstream", "upstream" in nginx)

    # ── Summary ─────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    if all_pass:
        print("ALL PRODUCTION TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    print(f"{'='*60}\n")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
