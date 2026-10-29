"""The market panel: a dense (day x mandi) view of one crop with an explicit
reporting mask. Nothing is imputed; a forward-filled view carries a staleness
counter so a stale price can never pass for an observed one."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import pandas as pd

from mandisense_ai.farmer import registry
from mandisense_ai.market_choice.config import MIN_REPORTED_DAYS, PANEL_FILE


@dataclass(frozen=True)
class Panel:
    crop: str
    dates: pd.DatetimeIndex            # (T,) every calendar day
    markets: Tuple[str, ...]           # registry mandi ids
    price: np.ndarray                  # (T, M) Rs/quintal, NaN when the mandi did not report
    arrivals: np.ndarray               # (T, M) tonnes
    mask: np.ndarray                   # (T, M) bool

    @property
    def T(self) -> int:
        return len(self.dates)

    @property
    def M(self) -> int:
        return len(self.markets)

    @property
    def coords(self) -> np.ndarray:
        return np.array([[registry.MANDIS[m].lat, registry.MANDIS[m].lon] for m in self.markets])

    def dist_km(self, origin: Tuple[float, float]) -> np.ndarray:
        return np.array([registry.haversine_km(origin, (registry.MANDIS[m].lat, registry.MANDIS[m].lon)) for m in self.markets])


def load_long(path=PANEL_FILE) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["date", "crop", "mandi_id", "price", "arrivals"])
    frame = pd.read_parquet(path)
    frame["date"] = pd.to_datetime(frame["date"])
    return frame


def build_panel(long: pd.DataFrame, crop: str, min_reported_days: int = MIN_REPORTED_DAYS) -> Optional[Panel]:
    sub = long[long["crop"] == crop]
    if sub.empty:
        return None
    counts = sub.groupby("mandi_id")["date"].nunique().sort_values(ascending=False)
    markets = tuple(m for m, n in counts.items() if n >= min_reported_days)
    if not markets:
        return None
    dates = pd.date_range(sub["date"].min(), sub["date"].max(), freq="D")
    price = sub.pivot(index="date", columns="mandi_id", values="price").reindex(index=dates, columns=list(markets))
    arr = sub.pivot(index="date", columns="mandi_id", values="arrivals").reindex(index=dates, columns=list(markets))
    p = price.to_numpy(dtype=float)
    return Panel(crop=crop, dates=dates, markets=markets, price=p, arrivals=arr.to_numpy(dtype=float), mask=~np.isnan(p))


def staleness(mask: np.ndarray, cap: int = 60) -> np.ndarray:
    """Days since each mandi last reported, as known at the END of each day (0 = reported that day)."""
    T, M = mask.shape
    out = np.full((T, M), float(cap))
    last = np.full(M, -1_000_000)
    for t in range(T):
        last = np.where(mask[t], t, last)
        out[t] = np.minimum(t - last, cap)
    return out


def ffill_price(price: np.ndarray) -> np.ndarray:
    return pd.DataFrame(price).ffill().to_numpy()
