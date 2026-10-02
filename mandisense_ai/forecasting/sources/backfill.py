"""
One-time history backfill into the observation store.

The live feed is a daily snapshot with no historical range query, so on day
one the store would be empty and nothing could be trained. This module seeds
it from the archives already in the repository:

* `data/processed/*.parquet` — the real Agmarknet archive for the five
  national benchmark markets (Kolar, Lasalgaon, Agra, Neemuch, Guntur),
  carrying genuine daily prices *and* arrival volume back to 2016. Only rows
  flagged as real trading days are taken; imputed/carried-forward rows are
  skipped so they cannot masquerade as observations the market actually made.

* `data/raw/agmarknet_*.csv` — the underlying scrapes, used only where a
  processed parquet is unavailable.

Backfilled rows are tagged with their own `source` value so a later audit can
always separate seeded history from live-ingested observations.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd

from mandisense_ai.forecasting.naming import canonical_commodity, canonical_market
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

SOURCE_NAME = "archive_backfill"


def _processed_dir() -> Path:
    from mandisense_ai.config.settings import settings

    return Path(settings.paths.processed_data)


def load_archive_history() -> pd.DataFrame:
    """
    Read every processed benchmark-market parquet into observation rows.

    Returns an empty frame rather than raising when no archive is present, so
    a fresh deployment can still run live-only ingestion.
    """
    directory = _processed_dir()
    if not directory.exists():
        logger.warning("Processed archive directory missing: %s", directory)
        return pd.DataFrame()

    rows: List[pd.DataFrame] = []
    ingested_at = datetime.utcnow().isoformat() + "Z"

    for path in sorted(directory.glob("*.parquet")):
        # `*_features.parquet` are byte-identical compatibility copies written
        # by the preprocessing pipeline; reading both would double-count.
        if path.name.endswith("_features.parquet"):
            continue

        stem_parts = path.stem.split("_")
        if len(stem_parts) < 2:
            continue
        commodity = canonical_commodity("_".join(stem_parts[:-1]))
        mandi_id = canonical_market(stem_parts[-1])
        if not commodity or not mandi_id:
            continue

        try:
            available = set(pd.read_parquet(path, engine="pyarrow").columns)
        except Exception as exc:  # pragma: no cover
            logger.error("Unreadable archive %s: %s", path.name, exc)
            continue

        wanted = [c for c in ("date", "modal_price", "arrivals_tonnes", "is_trading_day", "state") if c in available]
        if "date" not in wanted or "modal_price" not in wanted:
            logger.warning("Skipping %s: missing date/modal_price", path.name)
            continue

        frame = pd.read_parquet(path, columns=wanted, engine="pyarrow")
        frame["date"] = pd.to_datetime(frame["date"])

        if "is_trading_day" in frame.columns:
            # Imputed rows carry no new information and would create phantom
            # observations on days the mandi never traded.
            frame = frame[frame["is_trading_day"].astype(bool)]

        frame = frame[pd.to_numeric(frame["modal_price"], errors="coerce") > 0]
        if frame.empty:
            continue

        rows.append(
            pd.DataFrame(
                {
                    "date": frame["date"].dt.normalize(),
                    "commodity": commodity,
                    "mandi_id": mandi_id,
                    "modal_price": pd.to_numeric(frame["modal_price"], errors="coerce"),
                    "min_price": None,
                    "max_price": None,
                    "arrivals": pd.to_numeric(frame["arrivals_tonnes"], errors="coerce")
                    if "arrivals_tonnes" in frame.columns
                    else None,
                    "state": frame["state"] if "state" in frame.columns else None,
                    "district": None,
                    "source": SOURCE_NAME,
                    "ingested_at": ingested_at,
                }
            )
        )
        logger.info("Backfill prepared %s/%s: %d observations", commodity, mandi_id, len(frame))

    if not rows:
        return pd.DataFrame()

    return pd.concat(rows, ignore_index=True)


# ── Karnataka operating region (v4 processed dataset) ──────────────────────

V4_SOURCE_NAME = "v4_karnataka_backfill"


def _v4_dir() -> Path:
    from mandisense_ai.config.settings import settings

    return Path(settings.paths.processed_data) / "v4"


def load_v4_karnataka_history() -> pd.DataFrame:
    """
    Seed the observation store with the Karnataka operating region.

    The benchmark-market parquets above carry deep national history, but they
    cover five markets in five different states — none of them the Karnataka
    mandis the cognition layer and the TraderOS views actually serve. Without
    this loader the forecasting system and the rest of the product address
    disjoint sets of markets, and every forecast lookup driven from the UI
    misses.

    `data/processed/v4/*.csv` is the same canonical dataset the cognition
    engine and the candlestick API read (5 commodities x 15 Karnataka APMCs,
    2023-01 onward), so seeding from it makes the forecast universe a superset
    of what the product can display.

    Only genuine trading days are taken: `is_missing` marks rows the
    preprocessing pipeline carried forward to keep the grid dense, and
    admitting them would invent prices on days the mandi never opened.
    """
    directory = _v4_dir()
    if not directory.exists():
        logger.warning("v4 processed directory missing: %s", directory)
        return pd.DataFrame()

    rows: List[pd.DataFrame] = []
    ingested_at = datetime.utcnow().isoformat() + "Z"

    for path in sorted(directory.glob("*.csv")):
        commodity = canonical_commodity(path.stem)
        if not commodity:
            logger.warning("Skipping %s: unmapped commodity", path.name)
            continue

        try:
            frame = pd.read_csv(path)
        except Exception as exc:  # pragma: no cover
            logger.error("Unreadable v4 dataset %s: %s", path.name, exc)
            continue

        required = {"date", "mandi_id", "price"}
        if not required.issubset(frame.columns):
            logger.warning("Skipping %s: missing %s", path.name, required - set(frame.columns))
            continue

        if "is_missing" in frame.columns:
            frame = frame[frame["is_missing"].astype(int) == 0]

        frame = frame[pd.to_numeric(frame["price"], errors="coerce") > 0]
        if frame.empty:
            continue

        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame = frame.dropna(subset=["date"])

        # The v4 ids are already canonical slugs; routing them through
        # canonical_market anyway keeps one definition of a mandi id, so an
        # alias added later cannot make this loader disagree with ingestion.
        mandi_ids = frame["mandi_id"].map(lambda value: canonical_market(value) or value)

        rows.append(
            pd.DataFrame(
                {
                    "date": frame["date"].dt.normalize(),
                    "commodity": commodity,
                    "mandi_id": mandi_ids,
                    "modal_price": pd.to_numeric(frame["price"], errors="coerce"),
                    "min_price": None,
                    "max_price": None,
                    "arrivals": pd.to_numeric(frame["arrivals"], errors="coerce")
                    if "arrivals" in frame.columns
                    else None,
                    "state": "Karnataka",
                    "district": None,
                    "source": V4_SOURCE_NAME,
                    "ingested_at": ingested_at,
                }
            )
        )
        logger.info(
            "v4 backfill prepared %s: %d observations across %d mandis",
            commodity,
            len(frame),
            mandi_ids.nunique(),
        )

    if not rows:
        return pd.DataFrame()

    return pd.concat(rows, ignore_index=True)


def load_all_history() -> pd.DataFrame:
    """
    Every bundled archive, national benchmark markets and Karnataka together.

    This is what a first run should seed from: the benchmark parquets supply
    the long history the models are trained on, the v4 dataset supplies the
    markets the product actually serves.
    """
    frames = [frame for frame in (load_archive_history(), load_v4_karnataka_history()) if not frame.empty]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)
