"""The farmer's net-revenue function and action space.

Actions (index layout, length A = M * N_HOLD + 1):

    a = m * N_HOLD + k      sell at market m after holding k days (k = 0..K_MAX)
    a = A - 1               sell to a local trader at the farm gate on day t

Net revenue per quintal of action (m, k) from origin l on decision day t:

    R = (1 - fee) * (1 - delta)^k * P(m, t+k)  -  tau * road * dist(l, m)  -  handling

and if market m did not report on day t+k the farmer still pays the trip but
sells at the discounted fallback price phi * mean(prices that did report). The
revenue is *affine in the price vector*, which is what makes the SPO+ surrogate
loss exact for this problem (Elmachtoub & Grigas, 2022).
"""

from __future__ import annotations

from typing import Tuple

import numpy as np

from gfmc.config import N_HOLD, Economics


def n_actions(n_markets: int) -> int:
    return n_markets * N_HOLD + 1


def hold_discount(econ: Economics) -> np.ndarray:
    """(N_HOLD,) value multiplier for k days of holding, net of the market fee."""
    k = np.arange(N_HOLD)
    return (1.0 - econ.market_fee) * (1.0 - econ.spoilage_per_day) ** k


def trip_cost(dist_km: np.ndarray, econ: Economics) -> np.ndarray:
    """(M,) Rs/quintal cost of taking produce to each market."""
    return econ.transport_per_q_km * econ.road_factor * dist_km + econ.handling


def revenue_from_prices(price_mk: np.ndarray, gate_price: np.ndarray, dist_km: np.ndarray, econ: Economics) -> np.ndarray:
    """Map a price tensor to the revenue of every action.

    price_mk   : (..., M, N_HOLD) price of market m at hold k
    gate_price : (...)            reference price for the farm-gate action
    dist_km    : (M,)             great-circle distance origin -> market
    returns    : (..., A)
    """
    disc = hold_discount(econ)                                   # (N_HOLD,)
    cost = trip_cost(dist_km, econ)                              # (M,)
    rev = price_mk * disc - cost[:, None]                        # (..., M, N_HOLD)
    flat = rev.reshape(*rev.shape[:-2], -1)                      # (..., M*N_HOLD)
    gate = (econ.farmgate_discount * gate_price)[..., None]      # (..., 1)
    return np.concatenate([flat, gate], axis=-1)


def action_labels(markets: Tuple[str, ...]) -> list[str]:
    out = [f"{m} +{k}d" for m in markets for k in range(N_HOLD)]
    return out + ["farm-gate"]


def decode(a: np.ndarray | int) -> Tuple[np.ndarray, np.ndarray]:
    """Action index -> (market index, hold days). The farm-gate action maps to (-1, 0)."""
    a = np.asarray(a)
    return np.where(a % 1 == 0, a // N_HOLD, 0), a % N_HOLD
