import numpy as np
import pytest

from gfmc import stats


def test_holm_matches_known_values():
    adj = stats.holm([0.01, 0.04, 0.03, 0.005])
    np.testing.assert_allclose(adj, [0.03, 0.06, 0.06, 0.02], atol=1e-12)


def test_block_bootstrap_ci_covers_true_mean():
    rng = np.random.default_rng(0)
    hits = 0
    for s in range(40):
        e = rng.normal(0, 1, 400)
        x = 5 + np.convolve(e, np.ones(5) / 5, mode="same")        # serially dependent, true mean 5
        m, lo, hi = stats.block_bootstrap_mean(x, block=14, reps=500, seed=s)
        hits += lo <= 5 <= hi
    assert hits >= 33                                               # ~95% nominal


def test_dm_detects_real_difference_and_not_noise():
    rng = np.random.default_rng(1)
    a = rng.normal(10, 2, 600)
    b = a + rng.normal(0, 1, 600)
    assert stats.dm_test(a, b + 0.5)["p"] < 0.001                    # a is truly better by 0.5
    assert stats.dm_test(a, b)["p"] > 0.01                           # pure noise


def test_mcs_keeps_best_and_drops_clearly_worse():
    rng = np.random.default_rng(2)
    base = rng.normal(100, 5, 500)
    losses = {"good": base + rng.normal(0, 1, 500), "also_good": base + rng.normal(0.1, 1, 500),
              "bad": base + 8 + rng.normal(0, 1, 500)}
    res = stats.model_confidence_set(losses, alpha=0.10, reps=600)
    assert "good" in res["survivors"] and "bad" not in res["survivors"]
