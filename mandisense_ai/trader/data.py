"""
Shared data access for the trader analytics package.

Every trader feature (spread scanner, volatility, analogs, position risk,
forward pricing, empirical scenarios) reads the same observation archive.
Two things are centralised here so no module gets them subtly wrong on its
own:

**Caching keyed on the file, not on time.** The archive is ~100k rows of
parquet; re-reading it per request would make a 15-mandi spread scan read it
once per mandi. The cache is invalidated by the file's modification time, so
a nightly ingest is picked up on the next request without a restart and
without a TTL guessing how stale is acceptable.

**Calendar horizons, not row offsets.** Mandis do not print every day.
"The price 3 days later" is resolved as the first print on or after
date + 3 days, within a tolerance — the same convention the forecasting
targets use (`forecasting/features._add_horizon_targets`). A positional
`shift(-3)` would silently mean "three prints later", which on a gappy
series can be a fortnight.
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from mandisense_ai.forecasting.naming import canonical_commodity, canonical_market
from mandisense_ai.forecasting.store import ObservationStore
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

_lock = threading.Lock()
_cache: Dict[str, object] = {"mtime": None, "frame": None}


def resolve(commodity: str, mandi_id: Optional[str] = None) -> Tuple[str, Optional[str]]:
    """Canonical ids, through the same mapping ingestion and forecasting use."""
    c = canonical_commodity(commodity) or str(commodity).strip().lower()
    m = None
    if mandi_id is not None:
        m = canonical_market(mandi_id) or str(mandi_id).strip().lower()
    return c, m


def load_panel() -> pd.DataFrame:
    """The full observation archive, cached until the file changes."""
    store = ObservationStore()
    try:
        mtime = store.path.stat().st_mtime if store.path.exists() else None
    except OSError:
        mtime = None

    with _lock:
        if _cache["frame"] is not None and _cache["mtime"] == mtime:
            return _cache["frame"]  # type: ignore[return-value]

        frame = store.read()
        if not frame.empty:
            frame = frame.copy()
            frame["date"] = pd.to_datetime(frame["date"]).dt.normalize()
            frame["modal_price"] = pd.to_numeric(frame["modal_price"], errors="coerce")
            frame["arrivals"] = pd.to_numeric(frame.get("arrivals"), errors="coerce")
            frame = frame[frame["modal_price"] > 0]
        _cache["frame"] = frame
        _cache["mtime"] = mtime
        return frame


def series(commodity: str, mandi_id: str) -> pd.DataFrame:
    """One (commodity, mandi) series: one row per date, sorted.

    Columns: date, price, arrivals. Duplicate prints on a date collapse to
    their median rather than whichever row happened to sort last.
    """
    c, m = resolve(commodity, mandi_id)
    panel = load_panel()
    if panel.empty:
        return pd.DataFrame(columns=["date", "price", "arrivals"])
    sub = panel[(panel["commodity"] == c) & (panel["mandi_id"] == m)]
    if sub.empty:
        return pd.DataFrame(columns=["date", "price", "arrivals"])
    out = (
        sub.groupby("date", as_index=False)
        .agg(price=("modal_price", "median"), arrivals=("arrivals", "median"))
        .sort_values("date")
        .reset_index(drop=True)
    )
    return out


def mandis_for(commodity: str) -> List[str]:
    c, _ = resolve(commodity)
    panel = load_panel()
    if panel.empty:
        return []
    return sorted(panel.loc[panel["commodity"] == c, "mandi_id"].unique().tolist())


def forward_returns(frame: pd.DataFrame, horizon_days: int) -> pd.Series:
    """Log return from each print to the first print >= date + horizon.

    Indexed like `frame`. NaN where no print lands within the tolerance
    window — an unresolvable outcome is left missing, never filled.
    """
    if frame.empty:
        return pd.Series(dtype=float)
    base = frame[["date", "price"]].reset_index(drop=True)
    probe = pd.DataFrame({"target": base["date"] + pd.Timedelta(days=horizon_days)})
    lookup = base.rename(columns={"date": "obs_date", "price": "future_price"})
    merged = pd.merge_asof(
        probe.reset_index().sort_values("target"),
        lookup.sort_values("obs_date"),
        left_on="target",
        right_on="obs_date",
        direction="forward",
        tolerance=pd.Timedelta(days=max(3, horizon_days)),
    ).sort_values("index")
    future = merged["future_price"].to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.log(future / base["price"].to_numpy())
    return pd.Series(result, index=frame.index)


def snapshot(
    commodity: str,
    window_days: int = 7,
    universe: Optional[List[str]] = None,
) -> Dict[str, object]:
    """Each mandi's most recent price, anchored to one comparable date.

    Comparing a price printed yesterday with one printed four months ago is
    not a spread, it is two different markets. The anchor date is the latest
    date on which at least half the mandis carrying this commodity had a
    print within the preceding `window_days`; each mandi contributes its
    latest print inside that window, or is listed as stale and left out.
    """
    c, _ = resolve(commodity)
    panel = load_panel()
    sub = panel[panel["commodity"] == c] if not panel.empty else panel
    if universe is not None and sub is not None and not sub.empty:
        # Restrict to the mandis the caller can actually act across. Without
        # this a single-day ingest from five states (hundreds of mandis with
        # one print each) out-votes the tracked mandis for the anchor date,
        # and every mandi with real history is reported stale.
        sub = sub[sub["mandi_id"].isin(universe)]
    if sub is None or sub.empty:
        return {"as_of": None, "prices": {}, "stale": list(universe or [])}

    mandis = sorted(sub["mandi_id"].unique())
    dates = sorted(sub["date"].unique(), reverse=True)
    # At least half of the mandis carrying this commodity, but never more
    # than there are: `max(2, ...)` here used to floor the requirement at 2
    # even when only one mandi exists (a restricted `universe`, or a
    # commodity tracked at a single mandi), which no anchor date could ever
    # satisfy -- snapshot() returned everything as stale, always.
    needed = min(len(mandis), max(1, int(np.ceil(len(mandis) / 2))))
    window = pd.Timedelta(days=window_days)

    anchor = None
    for d in dates:
        d = pd.Timestamp(d)
        active = sub[(sub["date"] <= d) & (sub["date"] > d - window)]["mandi_id"].nunique()
        if active >= needed:
            anchor = d
            break

    if anchor is None:
        return {"as_of": None, "prices": {}, "stale": mandis}

    in_window = sub[(sub["date"] <= anchor) & (sub["date"] > anchor - window)]
    latest = in_window.sort_values("date").groupby("mandi_id").tail(1)
    prices = {
        row.mandi_id: {"price": float(row.modal_price), "date": str(pd.Timestamp(row.date).date())}
        for row in latest.itertuples()
    }
    stale = [m for m in mandis if m not in prices]
    return {"as_of": str(anchor.date()), "prices": prices, "stale": stale}


HISTORICAL_LOOKBACK_DAYS = 730


def move_distribution(commodity: str, mandi_id: str, horizon_days: int) -> Dict[str, object]:
    """Where the price is likely to be `horizon_days` out, and on what basis.

    Two sources, in order of preference, and the one used is always named:

      * ``calibrated_forecast`` — the published forecast's interval for the
        nearest horizon, when the forecaster has an OK row for this series.
        Its 90% band covered 90.1-91.2% of outcomes in walk-forward
        backtest, so it is the stronger basis when it exists.
      * ``historical_returns`` — the empirical distribution of this series'
        own calendar-true `horizon_days` returns over the last two years.
        Used when there is no live forecast (a dormant or rebuilding
        series), which is exactly when a trader still needs a number.

    Returns base price and its date, plus quantile *returns* (log) so callers
    can apply them to any position size.
    """
    c, m = resolve(commodity, mandi_id)
    frame = series(c, m)
    if frame.empty:
        return {"status": "UNAVAILABLE", "reason": "No recorded prices for this series."}

    base_price = float(frame["price"].iloc[-1])
    base_date = pd.Timestamp(frame["date"].iloc[-1])
    age_days = int((pd.Timestamp.now().normalize() - base_date).days)

    try:
        from mandisense_ai.forecasting.service import get_forecast_service

        service = get_forecast_service()
        if service.is_available:
            row = service.nearest_horizon(c, m, horizon_days)
            interval = (row or {}).get("interval") or {}
            if row and row.get("status") == "OK" and interval.get("p05") and row.get("last_observed_price"):
                fbase = float(row["last_observed_price"])
                q = {
                    k: float(np.log(float(interval[k]) / fbase))
                    for k in ("p05", "p25", "p75", "p95")
                    if interval.get(k)
                }
                q["p50"] = float(np.log(float(row["forecast_price"]) / fbase))
                return {
                    "status": "OK",
                    "method": "calibrated_forecast",
                    "base_price": fbase,
                    "base_date": str(row.get("as_of_date")),
                    "age_days": row.get("data_lag_days"),
                    "horizon_days": row.get("horizon_days"),
                    "quantiles": q,
                    "sample_size": None,
                }
    except Exception as exc:  # the historical path below is the honest fallback
        logger.warning("Forecast band unavailable for %s/%s: %s", c, m, exc)

    recent = frame[frame["date"] >= base_date - pd.Timedelta(days=HISTORICAL_LOOKBACK_DAYS)].reset_index(drop=True)
    rets = forward_returns(recent, horizon_days).dropna()
    if len(rets) < 60:
        return {
            "status": "INSUFFICIENT_HISTORY",
            "reason": f"Only {len(rets)} resolvable {horizon_days}-day outcomes in the last two years.",
        }
    q = {
        "p05": float(rets.quantile(0.05)),
        "p25": float(rets.quantile(0.25)),
        "p50": float(rets.quantile(0.50)),
        "p75": float(rets.quantile(0.75)),
        "p95": float(rets.quantile(0.95)),
    }
    return {
        "status": "OK",
        "method": "historical_returns",
        "base_price": base_price,
        "base_date": str(base_date.date()),
        "age_days": age_days,
        "horizon_days": horizon_days,
        "quantiles": q,
        "sample_size": int(len(rets)),
        "returns": rets,
    }
