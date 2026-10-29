"""Tests of the novel components: SPO+ loss, conformal floor, revenue function.

Synthetic arrays below are used only to verify mathematical properties.
"""

import numpy as np
import pytest
import torch

from gfmc import econ as E
from gfmc.config import DEFAULT_ECON, K_MAX, N_HOLD, Conformal
from gfmc.conformal import run_floor, violation_rate
from gfmc.models.losses import regret, spo_plus


# ----------------------------------------------------------------- SPO+
def _rand(n=64, A=9, seed=0):
    g = torch.Generator().manual_seed(seed)
    r = torch.randn(n, A, generator=g)
    rh = torch.randn(n, A, generator=g)
    return rh, r, torch.ones(n, A, dtype=torch.bool)


def test_spo_plus_is_nonnegative_and_zero_at_truth():
    rh, r, m = _rand()
    assert (spo_plus(rh, r, m) >= -1e-6).all()
    assert torch.allclose(spo_plus(r, r, m), torch.zeros(len(r)), atol=1e-6)


def test_spo_plus_upper_bounds_regret():
    rh, r, m = _rand(2000, 9, 1)
    assert (spo_plus(rh, r, m) + 1e-5 >= regret(rh, r, m)).all()


def test_spo_plus_respects_the_offered_set():
    rh, r, m = _rand(50, 9, 2)
    r[:, 0] = 1e3                                  # a spectacular action that is NOT offered
    m[:, 0] = False
    assert (regret(rh, r, m) < 100).all()          # regret never measured against the forbidden action


def test_spo_plus_matches_brute_force_formula():
    rh, r, m = _rand(20, 7, 3)
    for i in range(len(r)):
        a_star = int(r[i].argmax())
        manual = max(2 * rh[i, a] - r[i, a] for a in range(7)) - 2 * rh[i, a_star] + r[i, a_star]
        assert float(spo_plus(rh[i:i + 1], r[i:i + 1], m[i:i + 1])) == pytest.approx(float(manual), abs=1e-5)


def test_spo_plus_gradient_pushes_toward_the_optimal_action():
    r = torch.tensor([[1.0, 5.0, 3.0]])
    rh = torch.tensor([[4.0, 1.0, 2.0]], requires_grad=True)       # wrongly prefers action 0
    m = torch.ones(1, 3, dtype=torch.bool)
    spo_plus(rh, r, m).sum().backward()
    g = rh.grad[0]
    assert g[1] < 0 and g[0] > 0                                    # raise optimum, lower the wrong pick


# ------------------------------------------------------------- revenue
def test_revenue_layout_and_values():
    M = 3
    price = np.full((2, M, N_HOLD), 2000.0)
    gate = np.array([2000.0, 2000.0])
    dist = np.array([0.0, 50.0, 100.0])
    r = E.revenue_from_prices(price, gate, dist, DEFAULT_ECON)
    assert r.shape == (2, E.n_actions(M))
    disc = E.hold_discount(DEFAULT_ECON)
    assert r[0, 0] == pytest.approx(2000 * disc[0] - DEFAULT_ECON.handling)
    assert r[0, 1] < r[0, 0]                                       # holding a day costs spoilage
    assert r[0, N_HOLD * 2] < r[0, 0]                              # farther market, lower net
    assert r[0, -1] == pytest.approx(DEFAULT_ECON.farmgate_discount * 2000)


def test_revenue_is_affine_in_prices():
    M = 4
    rng = np.random.default_rng(0)
    p1, p2 = rng.uniform(1000, 3000, (2, 1, M, N_HOLD))
    g1, g2 = np.array([1500.0]), np.array([2500.0])
    dist = rng.uniform(0, 100, M)
    f = lambda p, g: E.revenue_from_prices(p, g, dist, DEFAULT_ECON)
    lam = 0.37
    np.testing.assert_allclose(f(lam * p1 + (1 - lam) * p2, lam * g1 + (1 - lam) * g2),
                               lam * f(p1, g1) + (1 - lam) * f(p2, g2), rtol=1e-9)


# ------------------------------------------------------------ conformal
def _stream(n=1500, O=1, A=6, bias=300.0, seed=0):
    rng = np.random.default_rng(seed)
    R = rng.normal(2000, 400, (n, O, A))
    r_hat = R + rng.normal(bias, 150, (n, O, A)) + rng.normal(0, 150, (n, O, A))   # biased, noisy model
    return r_hat, R, np.ones((n, A), dtype=bool), np.arange(n) + 100, np.arange(n) + 99


def test_floor_coverage_holds_even_for_a_biased_model():
    r_hat, R, am, sale, today = _stream(bias=400.0)
    conf = Conformal(alpha=0.10, gamma=0.02)
    res = run_floor(r_hat, R, am, sale, today, conf)
    warm = 150
    v = violation_rate(R, res, np.arange(len(R)) >= warm)
    assert abs(v - 0.10) < 0.035


def test_floor_is_conservative_enough_when_tighter_alpha():
    r_hat, R, am, sale, today = _stream(bias=400.0, seed=1)
    lo = run_floor(r_hat, R, am, sale, today, Conformal(alpha=0.05, gamma=0.02))
    hi = run_floor(r_hat, R, am, sale, today, Conformal(alpha=0.20, gamma=0.02))
    assert violation_rate(R, lo) < violation_rate(R, hi)
    assert lo.floor.mean() < hi.floor.mean()                          # a stricter guarantee is a lower floor


def test_floor_procedure_never_reads_future_outcomes():
    r_hat, R, am, sale, today = _stream(n=400, seed=2)
    base = run_floor(r_hat, R, am, sale, today)
    d0 = 250
    R2 = R.copy()
    R2[d0 - K_MAX:] = R2[d0 - K_MAX:] * 0.2 + 5.0                      # corrupt outcomes that are NOT yet known at d0
    other = run_floor(r_hat, R2, am, sale, today)
    np.testing.assert_array_equal(base.chosen[:d0], other.chosen[:d0])
    np.testing.assert_allclose(base.floor[:d0], other.floor[:d0])


def test_floor_respects_offered_actions():
    r_hat, R, am, sale, today = _stream(n=300, seed=3)
    am[:, 0] = False
    r_hat[:, :, 0] = 1e6
    res = run_floor(r_hat, R, am, sale, today)
    assert (res.chosen != 0).all()
