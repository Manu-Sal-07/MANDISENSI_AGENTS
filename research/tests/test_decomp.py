import numpy as np
import pytest

from gfmc import decomp


def _signal(n=500, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    return 7.0 + 0.002 * t + 0.3 * np.sin(2 * np.pi * t / 60) + 0.1 * np.sin(2 * np.pi * t / 7) + rng.normal(0, 0.03, n)


@pytest.mark.parametrize("name", ["STL", "VMD"])
def test_components_sum_to_signal(name):
    y = _signal()
    c = decomp.DECOMPOSERS[name](y)
    assert c.shape[0] == len(y)
    np.testing.assert_allclose(c.sum(1), y, atol=1e-8)


def test_vmd_modes_are_ordered_low_to_high_frequency():
    y = _signal(600)
    m = decomp.vmd(y - y.mean(), K=4)
    # zero-crossing rate rises with centre frequency
    zc = [np.mean(np.diff(np.sign(m[:, k])) != 0) for k in range(m.shape[1])]
    assert zc[0] <= zc[-1]


def test_vmd_slow_mode_tracks_the_slow_component():
    y = _signal(600)
    c = decomp.vmd_decompose(y, K=4)
    t = np.arange(600)
    low = 7.0 + 0.002 * t + 0.3 * np.sin(2 * np.pi * t / 60)       # all content below the weekly band
    assert np.corrcoef(c[:, 0] + c[:, 1], low)[0, 1] > 0.95


@pytest.mark.parametrize("name", ["STL", "VMD"])
def test_global_decomposition_is_not_causal(name):
    """The published practice leaks: components at t move when the future changes."""
    y = _signal(400)
    s = decomp.future_sensitivity(decomp.DECOMPOSERS[name], y, t=250)
    assert s > 1e-3


@pytest.mark.parametrize("name", ["STL", "VMD"])
def test_decomposing_only_the_past_is_exactly_causal(name):
    y = _signal(400)
    t = 250
    f = decomp.DECOMPOSERS[name]
    a = f(y[: t + 1])
    y2 = y.copy()
    y2[t + 1:] += 5.0                                  # a different future
    b = f(y2[: t + 1])
    np.testing.assert_array_equal(a, b)


def test_identity_decomposition_makes_causal_joint_equal_the_raw_control():
    """Positive control: if 'decomposition' returns the series itself, causal_joint must equal the raw control."""
    import pandas as pd
    from gfmc import decomp, leakage

    rng = np.random.default_rng(0)
    n = 700
    y = 7 + np.cumsum(rng.normal(0, 0.02, n))
    dates = pd.date_range("2022-01-01", periods=n)
    decomp.DECOMPOSERS["ID"] = lambda x: np.asarray(x, float).reshape(-1, 1)
    try:
        df = leakage.run_series(y, np.ones(n, bool), dates, "ID", "ridge", hs=(1,), test_start="2023-06-01", step=3,
                                refit_days=60, min_history=200)
    finally:
        del decomp.DECOMPOSERS["ID"]
    np.testing.assert_allclose(df["causal_joint"], df["raw"], atol=1e-9)
    np.testing.assert_allclose(df["published_joint"], df["causal_joint"], atol=1e-9)    # identity has no look-ahead either
