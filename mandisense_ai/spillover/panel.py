"""
Multi-commodity panel construction.

Loads the processed market datasets and aligns them onto a common calendar so
that lead/lag relationships between commodities are measured against the same
time axis.

Only genuine trading observations are used. Imputed / carried-forward rows are
excluded, because a forward-filled price creates an artificial zero return that
biases both volatility and cross-correlation toward zero.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from mandisense_ai.spillover.config import SpilloverConfig, DEFAULT_CONFIG
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

_REQUIRED_COLUMNS = ("date", "modal_price")
_OPTIONAL_COLUMNS = ("is_trading_day", "supply_regime", "supply_stress_score", "arrivals_tonnes")


@dataclass(frozen=True)
class CommodityPanel:
    """
    An aligned multi-commodity panel.

    Attributes:
        prices: period-end price per commodity (columns = commodity).
        returns: log returns of ``prices``.
        regimes: period-end supply regime label per commodity.
        stress: period-mean supply stress score per commodity.
        markets: commodity -> source market id, retained for provenance because
            each commodity is sourced from a different physical mandi.
        data_hash: content hash of the underlying price panel.
    """

    prices: pd.DataFrame
    returns: pd.DataFrame
    regimes: pd.DataFrame
    stress: pd.DataFrame
    markets: Dict[str, str]
    data_hash: str

    @property
    def commodities(self) -> List[str]:
        return list(self.prices.columns)

    @property
    def n_periods(self) -> int:
        return int(len(self.prices))

    def describe(self) -> Dict:
        return {
            "commodities": self.commodities,
            "markets": dict(self.markets),
            "n_periods": self.n_periods,
            "start": str(self.prices.index.min().date()) if self.n_periods else None,
            "end": str(self.prices.index.max().date()) if self.n_periods else None,
            "data_hash": self.data_hash,
        }


def _discover_datasets(processed_dir: Path) -> Dict[str, Path]:
    """
    Map commodity -> dataset path.

    ``*_features.parquet`` files are byte-identical compatibility copies written
    by the preprocessing pipeline, so they are skipped to avoid double counting.
    """
    found: Dict[str, Path] = {}
    for path in sorted(processed_dir.glob("*.parquet")):
        if path.name.endswith("_features.parquet"):
            continue
        stem_parts = path.stem.split("_")
        if len(stem_parts) < 2:
            continue
        commodity = "_".join(stem_parts[:-1])
        if commodity in found:
            logger.warning(
                "Duplicate dataset for commodity %s (%s ignored)", commodity, path.name
            )
            continue
        found[commodity] = path
    return found


def _load_one(path: Path) -> Optional[pd.DataFrame]:
    try:
        available = set(pd.read_parquet(path, engine="pyarrow").columns)
    except Exception as exc:  # pragma: no cover - corrupt file guard
        logger.error("Unable to read %s: %s", path.name, exc)
        return None

    missing = [c for c in _REQUIRED_COLUMNS if c not in available]
    if missing:
        logger.warning("Skipping %s: missing columns %s", path.name, missing)
        return None

    columns = list(_REQUIRED_COLUMNS) + [c for c in _OPTIONAL_COLUMNS if c in available]
    df = pd.read_parquet(path, columns=columns, engine="pyarrow")
    df["date"] = pd.to_datetime(df["date"])

    if "is_trading_day" in df.columns:
        # Imputed rows carry no new information; including them manufactures
        # zero returns and deflates every correlation in the panel.
        df = df[df["is_trading_day"].astype(bool)]

    df = df[df["modal_price"] > 0]
    return df.sort_values("date").set_index("date")


def build_panel(
    processed_dir: Path,
    config: SpilloverConfig = DEFAULT_CONFIG,
) -> CommodityPanel:
    """
    Construct an aligned panel from the processed datasets.

    Raises:
        ValueError: if fewer than two commodities are usable, or if the
            jointly-observed history is shorter than ``min_overlap_periods``.
            Spillover is undefined in both cases, so failing loudly here is
            preferable to emitting an empty artifact.
    """
    processed_dir = Path(processed_dir)
    datasets = _discover_datasets(processed_dir)
    if len(datasets) < 2:
        raise ValueError(
            f"Spillover needs at least 2 commodities; found {len(datasets)} in {processed_dir}"
        )

    price_cols: Dict[str, pd.Series] = {}
    regime_cols: Dict[str, pd.Series] = {}
    stress_cols: Dict[str, pd.Series] = {}
    markets: Dict[str, str] = {}

    for commodity, path in datasets.items():
        df = _load_one(path)
        if df is None or df.empty:
            continue

        freq = config.frequency
        price_cols[commodity] = df["modal_price"].resample(freq).last()
        markets[commodity] = path.stem.split("_")[-1]

        if "supply_regime" in df.columns:
            regime_cols[commodity] = df["supply_regime"].resample(freq).last()
        if "supply_stress_score" in df.columns:
            stress_cols[commodity] = df["supply_stress_score"].resample(freq).mean()

    if len(price_cols) < 2:
        raise ValueError(f"Only {len(price_cols)} commodities produced usable series")

    prices = pd.DataFrame(price_cols).dropna(how="any")
    if len(prices) < config.min_overlap_periods:
        raise ValueError(
            f"Insufficient overlapping history: {len(prices)} periods "
            f"< required {config.min_overlap_periods}"
        )

    returns = np.log(prices).diff()

    regimes = (
        pd.DataFrame(regime_cols).reindex(prices.index)
        if regime_cols
        else pd.DataFrame(index=prices.index)
    )
    stress = (
        pd.DataFrame(stress_cols).reindex(prices.index)
        if stress_cols
        else pd.DataFrame(index=prices.index)
    )

    data_hash = hashlib.sha256(
        pd.util.hash_pandas_object(prices.round(6), index=True).values
    ).hexdigest()[:16]

    logger.info(
        "Panel built: %d commodities x %d periods (%s -> %s)",
        prices.shape[1],
        prices.shape[0],
        prices.index.min().date(),
        prices.index.max().date(),
    )

    return CommodityPanel(
        prices=prices,
        returns=returns,
        regimes=regimes,
        stress=stress,
        markets=markets,
        data_hash=data_hash,
    )
