"""Shared fixtures. Tests use small *fabricated* frames only to exercise code
paths; none of that data is ever used for results."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def toy_long():
    """Three markets, 200 days, deterministic prices with some silent days."""
    rng = np.random.default_rng(0)
    dates = pd.date_range("2022-01-01", periods=200, freq="D")
    markets = ["Kolar APMC", "Mulbagal APMC", "Bangarpet APMC"]
    rows = []
    base = 1500 + 300 * np.sin(np.arange(200) / 20)
    for j, m in enumerate(markets):
        for t, d in enumerate(dates):
            if rng.random() < 0.15 and t > 0:   # silent day
                continue
            rows.append({"date": d, "state": "Karnataka", "district": "Kolar", "market": m, "commodity": "Tomato",
                         "price": float(base[t] * (1 + 0.05 * j) * np.exp(rng.normal(0, 0.03))),
                         "arrivals": float(rng.uniform(5, 50)), "source": "test"})
    return pd.DataFrame(rows)
