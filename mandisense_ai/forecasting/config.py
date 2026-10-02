"""
Configuration for the scheduled forecasting system.

Every tunable that affects a published forecast lives here, so a forecast
artifact can record exactly which configuration produced it.

Design stance
-------------
This system is **offline training + offline (batch) inference**. Nothing is
trained or scored inside a request. A nightly job ingests yesterday's market
observations, rebuilds features, scores every (commodity, mandi, horizon)
cell, and publishes a forecast table. Serving is an O(1) lookup against that
table. Online/incremental training is deliberately excluded: it is expensive,
hard to validate, and buys nothing for a market that prints once a day.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Tuple

from mandisense_ai.utils.exceptions import ConfigurationError
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

# ── Data source ────────────────────────────────────────────────────────────

# data.gov.in "Current Daily Price of Various Commodities from Various
# Markets (Mandi)" — the free, government-published Agmarknet feed. It is a
# *current day snapshot*, not a historical archive, which is precisely why
# ingestion has to run on a schedule: history accumulates one day at a time.
DATAGOV_RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
DATAGOV_BASE_URL = "https://api.data.gov.in/resource"

# data.gov.in publishes this rate-limited key for evaluation. Override with a
# registered key via DATAGOV_API_KEY for production throughput.
DATAGOV_PUBLIC_SAMPLE_KEY = "579b464db66ec23bdd000001cdd3946e44ce4aad7209ff7b23ac571b"


def get_api_key() -> str:
    """
    The data.gov.in key to authenticate ingestion with.

    Falling back to the shared sample key is fine for local development, where
    the fetch is occasional and manual. It is a silent liability in
    production: that key is shared across every user of the free tier, so its
    rate limit can be exhausted by traffic this deployment never sent, and a
    run that starts failing for that reason looks identical in the logs to
    the feed itself being down. Mirrors the same environment-gated fail-fast
    already used for the database startup check in `api/main.py`, rather than
    inventing a second convention for the same distinction.
    """
    key = os.getenv("DATAGOV_API_KEY")
    if key:
        return key

    if os.getenv("APP__ENVIRONMENT", "development").lower() == "production":
        raise ConfigurationError(
            "DATAGOV_API_KEY is not set. Refusing to fall back to the shared "
            "public sample key in production, where its rate limit is shared "
            "with every other free-tier caller and its exhaustion is "
            "indistinguishable in the logs from the upstream feed being down."
        )

    logger.warning(
        "DATAGOV_API_KEY not set — using the rate-limited public sample key. "
        "Fine for local development; set a registered key before scheduling "
        "this in production."
    )
    return DATAGOV_PUBLIC_SAMPLE_KEY


# ── Ingestion targets ──────────────────────────────────────────────────────

# Commodity names as they appear in the upstream feed, mapped to the
# canonical ids this codebase already uses everywhere else.
COMMODITY_ALIASES: Dict[str, str] = {
    "tomato": "tomato",
    "onion": "onion",
    "potato": "potato",
    "garlic": "garlic",
    "ginger": "ginger",
    "ginger(green)": "ginger",
    "green ginger": "ginger",
    "dry chillies": "dry_chillies",
    "chilly capsicum": "dry_chillies",
}

TARGET_COMMODITIES: Tuple[str, ...] = (
    "tomato", "onion", "potato", "garlic", "ginger", "dry_chillies",
)
"""`dry_chillies` has bounds in `validation.py`, aliases above, and years of
archived history in the observation store — but was missing from this tuple,
so the nightly ingest never fetches it while training keeps including it
regardless (it derives commodities from whatever the store already holds).
The result is a commodity that trains fine today and silently drifts to
DORMANT as its history ages past `max_observation_gap_days`, for no reason
visible anywhere in its own forecast output."""

# States pulled each night. Karnataka is the operating region; the others host
# the national benchmark markets that the historical archive is built from.
TARGET_STATES: Tuple[str, ...] = (
    "Karnataka",
    "Maharashtra",
    "Uttar Pradesh",
    "Madhya Pradesh",
    "Andhra Pradesh",
)


# ── Horizons ───────────────────────────────────────────────────────────────

# Direct multi-horizon: one model per horizon, each trained to predict h days
# ahead from today's features. Chosen over recursive forecasting (feeding a
# prediction back as an input) because recursive error compounds badly over a
# week and its uncertainty is not honestly quantifiable.
FORECAST_HORIZONS: Tuple[int, ...] = (1, 3, 5, 7)


@dataclass(frozen=True)
class ForecastConfig:
    """Immutable configuration for an ingest → train → forecast cycle."""

    # --- horizons ---
    horizons: Tuple[int, ...] = FORECAST_HORIZONS

    # --- history requirements ---
    min_history_days: int = 60
    """A (commodity, mandi) pair needs this much history before any forecast
    is published for it. Below this, lag and rolling features are unstable and
    the honest answer is 'not enough data', not a confident number."""

    max_observation_gap_days: int = 21
    """If the most recent observation is older than this, the series is
    treated as dormant and no forecast is published."""

    lookback_window: int = 120
    """Rows of history loaded per series when building inference features."""

    # --- feature engineering ---
    price_lags: Tuple[int, ...] = (1, 2, 3, 7, 14)
    rolling_windows: Tuple[int, ...] = (7, 14, 30)
    use_arrivals: bool = True
    """Arrival-derived features are built only where arrivals exist. The free
    daily feed publishes price but not arrival volume, so the feature set is
    price-primary by design and degrades cleanly when arrivals are absent."""

    use_segment_aware_features: bool = True
    """Compute every windowed feature *within* a series' current continuity
    segment, so no lag or rolling window reaches back across a trading break.

    Without this, lags and rolling windows are positional: `price_lag_14` is
    'fourteen rows ago' regardless of whether those rows are last fortnight or
    eighteen months ago. A mandi that stopped trading in 2024 and resumed in
    2026 is refused on its first print (`days_since_prev` is huge) and then
    accepted on its *second*, at which point `days_since_prev` is 1 while
    `price_lag_14` and `roll_mean_30` still describe the 2024 market. The
    model is handed a 3x 'spike' that is really just the new price level, and
    confidently forecasts a crash back to a price that no longer exists.

    Segmenting fixes both halves: the stale values become missing (which
    XGBoost routes natively, and which the model has seen throughout training
    because every real series start looks the same way), and the series
    becomes serveable as soon as it has genuine recent history rather than
    waiting for the gap to age out of the window."""

    min_segment_observations: int = 11
    """In-segment observations required before a series is forecast again
    after a break.

    Not a round number: it is the point at which the *longest* rolling
    statistic first has enough in-segment support to be computed at all.
    `rolling_windows` tops out at 30 and each window uses
    `min_periods = max(2, window // 3)`, so `roll_mean_30` needs 10 prior
    observations within the segment, which a row reaches on its 11th. Below
    it the long-window features are all missing and the model degenerates
    toward a commodity-level average -- not worth publishing as a
    mandi-specific forecast. Above it the series is served with exactly the
    support the training regime also saw at every real series start.

    Reported as REBUILDING_HISTORY with the count still needed, so the wait is
    visible and finite rather than looking like a broken pipeline."""

    use_absence_features: bool = True
    """Attach panel-identified absence features (see `absence.py`). A day with
    no print is not noise: separating 'the mandi was open and this commodity
    did not trade' from 'the report never arrived' turns a dropped row into a
    supply signal."""

    use_seasonal_climatology: bool = True
    """Attach the leak-free seasonal-deviation feature (see `seasonal.py`):
    how far today's price sits from the historical norm for this time of
    year, where 'historical norm' means only years strictly before the one
    this row belongs to. This is the actual seasonality signal the system was
    missing — the agent named for it computed month-of-year and day-of-week
    integers and called that seasonality, which gives a tree splits to
    reconstruct the pattern from scratch rather than a direct answer."""

    seasonal_bucket_days: int = 15
    """Calendar granularity for the climatology reference (~24 buckets/year).
    Coarser than daily on purpose: with years of gappy data, a bucket this
    wide accumulates enough same-period observations per year to make the
    reference median stable, where an exact day-of-year match would mostly
    return a single noisy print or nothing at all."""

    price_arrival_elasticity_window: int = 30
    """Trailing window (observations, not calendar days) for the rolling
    log-log price/arrival elasticity feature. Same economic signal Stack A's
    arrival agent already computes well in a Python loop; here it is the
    closed-form rolling covariance/variance ratio, which is the same number
    without an O(n * window) per-row regression fit."""

    # --- serve-time feature availability ---
    arrival_dropout_rate: float = 0.35
    """Fraction of training rows whose arrival features are masked at fit time.

    The archive carries arrivals on 99.5% of rows; the live feed carries them
    on none, because the free resource does not publish volume. A model fit
    only on rows where arrivals exist has never seen the regime it will
    actually be served in. Masking a share of rows during training forces it
    to remain accurate on price alone, so the day ingestion switches over is
    not the day skill silently collapses. Set to 0.0 to disable."""

    # --- observation quality ---
    use_quality_weights: bool = True
    """Pass the ingest-time `quality_score` to the learner as a per-row sample
    weight, so a doubtful observation contributes proportionally less to the
    fit instead of either being deleted or being trusted completely."""

    min_quality_for_training: float = 0.10
    """Rows scoring below this are excluded from fitting altogether. They are
    still stored — the record of what the feed published is not the same thing
    as the record of what the model should learn from."""

    # --- training ---
    # Daily spot returns are close to a random walk: the signal-to-noise ratio
    # is low enough that an unregularised booster fits noise and ends up worse
    # than doing nothing. Measured on this archive, depth-6/400-tree settings
    # scored -0.07 to -0.19 skill (worse than naive); these shallow, heavily
    # penalised settings score positive at every horizon. Shrinkage is not a
    # detail here, it is the difference between a usable model and a harmful one.
    n_estimators: int = 150
    learning_rate: float = 0.03
    max_depth: int = 2
    subsample: float = 0.8
    colsample_bytree: float = 0.7
    min_child_weight: int = 50
    reg_lambda: float = 20.0
    random_seed: int = 20260916

    walk_forward_folds: int = 4
    min_train_rows: int = 250

    # --- promotion gate ---
    require_beat_baseline: bool = True
    """A challenger model is promoted only if it beats the naive
    (price unchanged over the horizon) baseline on held-out folds. A model
    that cannot beat 'next week looks like today' has no business being served."""

    baseline_improvement_margin: float = 0.005
    """Mean MAE improvement the challenger must show over the baseline."""

    min_fold_win_rate: float = 0.75
    """Fraction of walk-forward folds in which the challenger must beat the
    baseline. Realistic skill here is a couple of percent, which a single
    lucky fold can manufacture on the mean alone; requiring the win to repeat
    across folds is what separates a small real edge from noise."""

    # --- ensemble blend ---
    use_model_blend: bool = True
    """Fit a second, structurally different model (regularised linear,
    alongside the tree-based point model) and measure — on the same
    walk-forward folds used for the point model's own promotion — whether an
    inverse-error-weighted blend of the two beats the point model alone.
    Never hand-tuned: the blend weight is derived from each fold's own
    held-out error, not picked to look good on one dataset."""

    blend_improvement_margin: float = 0.002
    """Mean MAE improvement the blend must show over the single point model
    to be served in its place. Smaller than `baseline_improvement_margin`
    deliberately: beating a naive baseline is a low bar the point model has
    already cleared, whereas beating an already-validated, already-promoted
    model is the harder, second bar a blend has to earn on its own."""

    # --- staleness policy (serving) ---
    fresh_max_age_hours: int = 30
    """A forecast run older than this is reported as STALE to callers."""

    def as_dict(self) -> Dict:
        payload = asdict(self)
        payload["horizons"] = list(self.horizons)
        payload["price_lags"] = list(self.price_lags)
        payload["rolling_windows"] = list(self.rolling_windows)
        return payload


DEFAULT_CONFIG = ForecastConfig()


# ── Storage layout ─────────────────────────────────────────────────────────

def _root() -> Path:
    from mandisense_ai.config.settings import settings

    return Path(settings.paths.processed_data).parent


def observations_path() -> Path:
    """Append-only market observation store (the ingested ground truth)."""
    return _root() / "observations" / "market_observations.parquet"


def ingestion_log_path() -> Path:
    return _root() / "observations" / "ingestion_runs.jsonl"


def ledger_path() -> Path:
    """Append-only record of every published forecast and its realised outcome.

    Every gate in this system was validated on history at training time. This
    is the file that lets those gates be checked against what actually
    happened afterwards."""
    return _root() / "observations" / "forecast_ledger.parquet"


def quarantine_path() -> Path:
    """Rows the quality gate refused, kept with their reason.

    Deleting a rejected row destroys the only evidence that would show the
    gate itself is miscalibrated. A gate that rejects nothing and a gate that
    rejects everything look identical in the logs if the rows are gone."""
    return _root() / "observations" / "rejected_observations.parquet"


def forecast_store_path() -> Path:
    """Published forecast table that the API serves from."""
    from mandisense_ai.config.settings import settings

    return Path(settings.paths.models_dir) / "forecasts" / "forecast_store.json"


def model_registry_dir() -> Path:
    from mandisense_ai.config.settings import settings

    return Path(settings.paths.models_dir) / "forecast_models"
