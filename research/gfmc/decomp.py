"""Signal decomposers used by the decomposition-hybrid forecasting literature.

Both return an array (T, C) whose rows sum to the input signal (`remainder`
absorbs any reconstruction error), with components in a *fixed, comparable
order* (STL: trend, seasonal, residual; VMD: modes sorted by centre frequency
low -> high, then remainder). A consistent order is what lets a component
model trained on one decomposition be applied to another.

Both are two-sided smoothers: the value of a component at day t depends on
data after t. That is exactly the property the leakage benchmark exposes.
"""

from __future__ import annotations

from typing import Callable, Dict

import numpy as np


def stl_decompose(y: np.ndarray, period: int = 7) -> np.ndarray:
    from statsmodels.tsa.seasonal import STL

    res = STL(np.asarray(y, float), period=period, robust=True).fit()
    return np.column_stack([res.trend, res.seasonal, res.resid])


def vmd(f: np.ndarray, K: int = 5, alpha: float = 2000.0, tau: float = 0.0, tol: float = 1e-6,
        max_iter: int = 300) -> np.ndarray:
    """Variational mode decomposition (Dragomiretskiy & Zosso, 2014); returns (T, K) modes.

    Implementation follows the published ADMM updates with mirror extension,
    no DC mode and spread-out initial centre frequencies. Modes are returned
    sorted by final centre frequency.
    """
    f = np.asarray(f, float)
    T0 = len(f)
    half = T0 // 2
    fm = np.concatenate([f[:half][::-1], f, f[half:][::-1]])
    T = len(fm)
    freqs = (np.arange(1, T + 1) / T) - 0.5 - 1.0 / T
    f_hat = np.fft.fftshift(np.fft.fft(fm))
    f_plus = f_hat.copy()
    f_plus[: T // 2] = 0.0

    u = np.zeros((K, T), dtype=complex)
    omega = (0.5 / K) * np.arange(K)
    lam = np.zeros(T, dtype=complex)
    pos = slice(T // 2, T)

    for _ in range(max_iter):
        u_prev = u.copy()
        for k in range(K):
            others = u.sum(0) - u[k]
            u[k] = (f_plus - others - lam / 2.0) / (1.0 + alpha * (freqs - omega[k]) ** 2)
            p = np.abs(u[k, pos]) ** 2
            omega[k] = (freqs[pos] @ p) / max(p.sum(), 1e-30)
        lam = lam + tau * (u.sum(0) - f_plus)
        diff = np.sum(np.abs(u - u_prev) ** 2) / T
        if diff <= tol:
            break

    modes = np.zeros((K, T))
    for k in range(K):
        full = np.zeros(T, dtype=complex)
        full[pos] = u[k, pos]
        full[1: T // 2 + 1] = np.conj(u[k, T // 2: T][::-1][: T // 2])
        full[0] = np.conj(full[-1])
        modes[k] = np.real(np.fft.ifft(np.fft.ifftshift(full)))
    start = half
    modes = modes[:, start: start + T0]
    order = np.argsort(omega)
    return modes[order].T


def vmd_decompose(y: np.ndarray, K: int = 5) -> np.ndarray:
    """VMD modes (low -> high frequency) plus a remainder so that rows sum to y."""
    y = np.asarray(y, float)
    mu = y.mean()
    modes = vmd(y - mu, K=K)
    out = np.column_stack([modes, (y - mu) - modes.sum(1)])
    out[:, 0] += mu                                   # the level lives in the slowest mode
    return out


DECOMPOSERS: Dict[str, Callable[[np.ndarray], np.ndarray]] = {
    "STL": stl_decompose,
    "VMD": vmd_decompose,
}


def future_sensitivity(decomposer: Callable[[np.ndarray], np.ndarray], y: np.ndarray, t: int,
                       bump: float = 0.10, back: int = 5) -> float:
    """How much do the components over days (t-back..t] move if the *future* y[t+1:] is changed by `bump`?

    Returned as max |change| in any component over those days, divided by the
    standard deviation of y. Exactly 0 for a causal procedure.
    """
    a = decomposer(y)
    y2 = y.copy()
    y2[t + 1:] = y2[t + 1:] + bump
    b = decomposer(y2)
    sl = slice(t - back + 1, t + 1)
    return float(np.max(np.abs(a[sl] - b[sl])) / max(np.std(y), 1e-12))
