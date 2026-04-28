"""
Prometheus Metrics Registry for MandiSense AI.

Defines all custom metrics and provides helper functions/decorators
to instrument the FastAPI application, database queries, cache operations,
and the ML prediction pipeline.

Design:
  • Singleton-like registry using global prometheus_client metrics
  • Labels for high-cardinality data (endpoint, method, commodity, mandi)
  • Explicit tracking of ML outcomes (confidence, regime, mode)
"""

import time
from functools import wraps
from typing import Any, Callable

from prometheus_client import Counter, Histogram, Gauge

# ═══════════════════════════════════════════════════════════════════════════════
# 1. API HTTP Metrics
# ═══════════════════════════════════════════════════════════════════════════════

HTTP_REQUESTS_TOTAL = Counter(
    "api_http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"]
)

HTTP_REQUEST_LATENCY = Histogram(
    "api_http_request_latency_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

# ═══════════════════════════════════════════════════════════════════════════════
# 2. System Metrics (DB & Cache)
# ═══════════════════════════════════════════════════════════════════════════════

DB_QUERY_LATENCY = Histogram(
    "db_query_latency_seconds",
    "Database query latency in seconds",
    ["query_type"]  # e.g., 'insert_prediction', 'history_fetch'
)

CACHE_OPERATIONS_TOTAL = Counter(
    "cache_operations_total",
    "Total cache operations (hit/miss/set/error)",
    ["operation", "status"] # operation: 'get', 'set'; status: 'hit', 'miss', 'ok', 'error'
)

# ═══════════════════════════════════════════════════════════════════════════════
# 3. ML Prediction Metrics
# ═══════════════════════════════════════════════════════════════════════════════

PREDICTIONS_TOTAL = Counter(
    "ml_predictions_total",
    "Total number of predictions generated",
    ["commodity", "mandi", "blend_mode"] # blend_mode: 'phase1_only', 'blended', etc.
)

PREDICTION_CONFIDENCE = Histogram(
    "ml_prediction_confidence",
    "Distribution of prediction confidence scores (0.0 to 1.0)",
    ["commodity", "blend_mode"],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

PREDICTION_MAGNITUDE = Histogram(
    "ml_prediction_magnitude_pct",
    "Distribution of predicted price change percentages",
    ["commodity"],
    buckets=[-20.0, -10.0, -5.0, -2.0, 0.0, 2.0, 5.0, 10.0, 20.0]
)

ACTIVE_MODELS_GAUGE = Gauge(
    "ml_active_models_count",
    "Number of active learned models currently loaded in memory"
)

# ═══════════════════════════════════════════════════════════════════════════════
# Helper Context Managers / Decorators
# ═══════════════════════════════════════════════════════════════════════════════

class track_db_latency:
    """Context manager to track DB query latency."""
    def __init__(self, query_type: str):
        self.query_type = query_type
        self.start_time = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        latency = time.perf_counter() - self.start_time
        DB_QUERY_LATENCY.labels(query_type=self.query_type).observe(latency)


def record_prediction_metrics(
    commodity: str,
    mandi: str,
    blend_mode: str,
    confidence: float,
    prediction: float,
):
    """Helper to record all relevant ML metrics for a single prediction."""
    PREDICTIONS_TOTAL.labels(
        commodity=commodity, mandi=mandi, blend_mode=blend_mode
    ).inc()
    
    PREDICTION_CONFIDENCE.labels(
        commodity=commodity, blend_mode=blend_mode
    ).observe(confidence)
    
    PREDICTION_MAGNITUDE.labels(
        commodity=commodity
    ).observe(prediction)
