"""Model-interface and decision-pipeline tests on small fabricated panels."""

import numpy as np
import pandas as pd
import pytest

from gfmc import econ as E
from gfmc import policy as P
from gfmc.config import DEFAULT_ECON, N_HOLD
from gfmc.data import panel as pn
from gfmc.dataset import build_decision_data
from gfmc.models.base import RandomWalk
from gfmc.models.gbm import LGBMModel, XGBModel
from gfmc.models.neural import DeepSetsModel


def _dd(toy_long, n_extra=0):
    p = pn.build_panel(toy_long, "Tomato", min_reported_days=10)
    return build_decision_data(p, warmup=20)


def _idx(dd):
    return np.flatnonzero(dd.valid)


def test_decision_arrays_have_consistent_shapes(toy_long):
    dd = _dd(toy_long)
    D, M = dd.D, dd.M
    assert dd.X.shape[:2] == (D, M)
    assert dd.Y.shape == (D, M, N_HOLD) == dd.obs.shape
    assert dd.action_mask().shape == (D, E.n_actions(M))
    assert dd.valid.any()


def test_realised_price_uses_fallback_only_when_silent(toy_long):
    dd = _dd(toy_long)
    rp = dd.realised_price(DEFAULT_ECON)
    np.testing.assert_allclose(rp[dd.obs], dd.P_obs[dd.obs])
    fb = DEFAULT_ECON.fallback_discount * np.broadcast_to(dd.P_ref[:, None, :], rp.shape)
    np.testing.assert_allclose(rp[~dd.obs], fb[~dd.obs])


@pytest.mark.parametrize("make", [lambda: RandomWalk(), lambda: LGBMModel(n_estimators=20),
                                  lambda: XGBModel(n_estimators=20),
                                  lambda: DeepSetsModel("mse_obs", epochs=2),
                                  lambda: DeepSetsModel("mse_filled", epochs=2),
                                  lambda: DeepSetsModel("spo", epochs=2),
                                  lambda: DeepSetsModel("spo", structured=True, epochs=2)])
def test_every_model_fits_and_predicts_the_right_shape(toy_long, make):
    dd = _dd(toy_long)
    idx = _idx(dd)
    tr, te = idx[: len(idx) // 2], idx[len(idx) // 2:]
    cols = dd.fs.cols("base", "silence")
    m = make().fit(dd, tr, DEFAULT_ECON, cols)
    y = m.predict(dd, te)
    assert y.shape == (len(te), dd.M, N_HOLD)
    assert np.isfinite(y).all()


def test_neural_models_start_at_the_random_walk(toy_long):
    dd = _dd(toy_long)
    idx = _idx(dd)
    m = DeepSetsModel("spo", epochs=0).fit(dd, idx[:50], DEFAULT_ECON, dd.fs.cols("base"))
    np.testing.assert_allclose(m.predict(dd, idx[50:60]), 0.0, atol=1e-6)


def test_structured_model_exposes_report_probabilities(toy_long):
    dd = _dd(toy_long)
    idx = _idx(dd)
    m = DeepSetsModel("spo", structured=True, epochs=2).fit(dd, idx[:80], DEFAULT_ECON, dd.fs.cols("base"))
    m.predict(dd, idx[80:100])
    rp = m.report_prob_
    assert rp.shape == (20, dd.M, N_HOLD) and ((rp > 0) & (rp < 1)).all()


def test_spo_training_learns_to_pick_the_best_market(toy_long):
    """Market 0 is systematically priced 40% higher: a decision-trained model must choose it."""
    long = toy_long.copy()
    long.loc[long["market"] == "Kolar APMC", "price"] *= 1.4
    dd = _dd(long)
    idx = _idx(dd)
    tr, te = idx[: int(len(idx) * 0.6)], idx[int(len(idx) * 0.6):]
    m = DeepSetsModel("spo", epochs=25, lr=1e-2, hidden=32).fit(dd, tr, DEFAULT_ECON, dd.fs.cols("base"))
    am = dd.action_mask()[te]
    R = P.realised_revenue(dd, te, DEFAULT_ECON)
    out = P.score(R, am, P.choose(P.revenue_from_logret(dd, te, m.predict(dd, te), DEFAULT_ECON), am), dd, te)
    kolar = dd.panel.markets.index("Kolar APMC")
    share = np.mean(out.chosen // N_HOLD == kolar)
    assert share > 0.6


def test_oracle_dominates_every_policy_and_regret_is_nonnegative(toy_long):
    dd = _dd(toy_long)
    idx = _idx(dd)
    am = dd.action_mask()[idx]
    R = P.realised_revenue(dd, idx, DEFAULT_ECON)
    for name in ("nearest_today", "highest_yesterday", "trailing_best", "farm_gate"):
        out = P.score(R, am, P.choose(P.heuristic_scores(name, dd, idx, DEFAULT_ECON), am), dd, idx)
        assert (out.regret >= -1e-9).all()
        assert out.revenue.mean() <= out.oracle.mean() + 1e-9


def test_policy_only_chooses_offered_actions(toy_long):
    dd = _dd(toy_long)
    idx = _idx(dd)
    am = dd.action_mask()[idx]
    r_hat = np.random.default_rng(0).normal(size=(len(idx), 5, E.n_actions(dd.M))) + 1e3
    a = P.choose(r_hat, am)
    assert am[np.arange(len(idx))[:, None], a].all()


def test_cvar_is_mean_of_the_worst_tail():
    x = np.arange(100.0)
    assert P.cvar(x, 0.10) == pytest.approx(np.mean(np.arange(10)))
