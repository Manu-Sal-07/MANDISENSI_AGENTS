"""The market panel: a dense (day x market) view of one crop with an explicit
reporting mask.

A cell is *observed* only if the mandi reported that day. Nothing is filled in
here; forward-filled views are derived downstream and always carry a staleness
counter so that "stale" can never masquerade as "observed".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from gfmc.config import MIN_REPORTED_DAYS
from gfmc.data import registry


@dataclass(frozen=True)
class Panel:
    crop: str
    dates: pd.DatetimeIndex            # (T,) every calendar day, Sundays included
    markets: Tuple[str, ...]           # (M,)
    price: np.ndarray                  # (T, M) Rs/quintal, NaN where not reported
    arrivals: np.ndarray               # (T, M) tonnes, NaN where not reported / invalid
    mask: np.ndarray                   # (T, M) bool, True where the mandi reported a price
    coords: np.ndarray                 # (M, 2) lat, lon

    @property
    def T(self) -> int:
        return len(self.dates)

    @property
    def M(self) -> int:
        return len(self.markets)

    def index_of(self, date: str | pd.Timestamp) -> int:
        return int(self.dates.get_loc(pd.Timestamp(date)))

    def slice_days(self, start: str, end: str) -> slice:
        """Positional slice for [start, end)."""
        i = int(self.dates.searchsorted(pd.Timestamp(start)))
        j = int(self.dates.searchsorted(pd.Timestamp(end)))
        return slice(i, j)

    def dist_km(self, origin: Tuple[float, float], road_factor: float = 1.0) -> np.ndarray:
        return np.array([registry.haversine_km(origin, tuple(c)) for c in self.coords]) * road_factor

    def summary(self) -> pd.DataFrame:
        rows = []
        for j, m in enumerate(self.markets):
            seen = np.flatnonzero(self.mask[:, j])
            rows.append({
                "market": m, "reported_days": int(self.mask[:, j].sum()),
                "coverage": float(self.mask[:, j].mean()),
                "first": self.dates[seen[0]].date() if len(seen) else None,
                "last": self.dates[seen[-1]].date() if len(seen) else None,
            })
        return pd.DataFrame(rows)


def build_panel(
    long: pd.DataFrame,
    crop: str,
    markets: Optional[Sequence[str]] = None,
    min_reported_days: int = MIN_REPORTED_DAYS,
    start: Optional[str] = None,
    end: Optional[str] = None,
) -> Panel:
    """Pivot the long frame into a dense panel for one crop.

    Markets default to every market with at least `min_reported_days` reported
    days, ordered by coverage (densest first) so that results are reproducible.
    """
    sub = long[long["commodity"] == crop]
    if sub.empty:
        raise ValueError(f"No rows for crop '{crop}'")
    start_ts = pd.Timestamp(start) if start else sub["date"].min()
    end_ts = pd.Timestamp(end) if end else sub["date"].max()
    sub = sub[(sub["date"] >= start_ts) & (sub["date"] <= end_ts)]

    counts = sub.groupby("market")["date"].nunique().sort_values(ascending=False)
    if markets is None:
        markets = [m for m, n in counts.items() if n >= min_reported_days]
    markets = tuple(markets)
    if not markets:
        raise ValueError("No market satisfies the minimum-coverage rule")

    dates = pd.date_range(start_ts, end_ts, freq="D")
    price = sub.pivot(index="date", columns="market", values="price").reindex(index=dates, columns=list(markets))
    arr = sub.pivot(index="date", columns="market", values="arrivals").reindex(index=dates, columns=list(markets))
    p = price.to_numpy(dtype=float)
    return Panel(
        crop=crop,
        dates=dates,
        markets=markets,
        price=p,
        arrivals=arr.to_numpy(dtype=float),
        mask=~np.isnan(p),
        coords=np.array([registry.coords(m) for m in markets], dtype=float),
    )


def staleness(mask: np.ndarray, cap: int = 60) -> np.ndarray:
    """Days since each market last reported, as known at the END of each day.

    0 means it reported that day. Before the first report the value is `cap`.
    """
    T, M = mask.shape
    out = np.full((T, M), float(cap))
    last = np.full(M, -1_000_000)
    for t in range(T):
        last = np.where(mask[t], t, last)
        out[t] = np.minimum(t - last, cap)
    return out


def ffill_price(price: np.ndarray) -> np.ndarray:
    """Forward-fill along time (the standard pipeline's treatment of silence)."""
    return pd.DataFrame(price).ffill().to_numpy()
