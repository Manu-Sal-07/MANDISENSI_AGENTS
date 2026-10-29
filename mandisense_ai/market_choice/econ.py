"""Net-revenue function and action space (affine in prices).

Action index layout, length A = M * N_HOLD + 1:
    a = m * N_HOLD + k     sell at mandi m after holding k days
    a = A - 1              sell to a local trader at the farm gate
"""

from __future__ import annotations

import numpy as np

from mandisense_ai.market_choice.config import N_HOLD, Economics


def n_actions(n_markets: int) -> int:
    return n_markets * N_HOLD + 1


def hold_discount(e: Economics) -> np.ndarray:
    k = np.arange(N_HOLD)
    return (1.0 - e.market_fee) * (1.0 - e.spoilage_per_day) ** k


def trip_cost(dist_km: np.ndarray, e: Economics) -> np.ndarray:
    return e.transport_per_q_km * e.road_factor * dist_km + e.handling


def revenue_from_prices(price_mk: np.ndarray, gate_price: np.ndarray, dist_km: np.ndarray, e: Economics) -> np.ndarray:
    """price_mk (..., M, N_HOLD), gate_price (...), dist_km (M,) -> revenue of every action (..., A)."""
    rev = price_mk * hold_discount(e) - trip_cost(dist_km, e)[:, None]
    flat = rev.reshape(*rev.shape[:-2], -1)
    gate = (e.farmgate_factor * gate_price)[..., None]
    return np.concatenate([flat, gate], axis=-1)


def decode(a: int, n_markets: int):
    """Action index -> (market index or None for the farm gate, hold days)."""
    if a >= n_markets * N_HOLD:
        return None, 0
    return a // N_HOLD, a % N_HOLD
