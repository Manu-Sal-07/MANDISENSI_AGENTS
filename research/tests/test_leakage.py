"""Structural leakage tests: the single most important property of the study.

If any of these fail, every downstream number is invalid.
"""

import numpy as np
import pandas as pd

from gfmc.data import panel as pn
from gfmc.dataset import build_decision_data
from gfmc.features import build_features


def _panel(toy_long, perturb_from=None):
    long = toy_long.copy()
    if perturb_from is not None:
        m = long["date"] >= pd.Timestamp(perturb_from)
        long.loc[m, "price"] = long.loc[m, "price"] * 7.0          # wildly different future
        long.loc[m, "arrivals"] = long.loc[m, "arrivals"] * 3.0
    return pn.build_panel(long, "Tomato", min_reported_days=10)


def test_features_at_s_do_not_depend_on_the_future(toy_long):
    cut = pd.Timestamp("2022-04-01")
    a = build_features(_panel(toy_long))
    b = build_features(_panel(toy_long, perturb_from=cut + pd.Timedelta(days=1)))
    s = int(_panel(toy_long).dates.get_loc(cut))
    # every feature row up to and including the cut must be identical
    np.testing.assert_allclose(a.X[: s + 1], b.X[: s + 1], rtol=0, atol=1e-12)
    assert not np.allclose(a.X[s + 5:], b.X[s + 5:])                # ...and the future really did change


def test_decision_features_end_the_day_before_the_decision(toy_long):
    p = _panel(toy_long)
    dd = build_decision_data(p, warmup=20)
    i = 40
    t = dd.days[i]
    # features for decision day t are the panel features of day t-1
    np.testing.assert_allclose(dd.X[i], dd.fs.X[t - 1])


def test_targets_are_strictly_future_prices(toy_long):
    p = _panel(toy_long)
    dd = build_decision_data(p, warmup=20)
    for i in (30, 60, 90):
        t = dd.days[i]
        for k in range(4):
            expect = p.price[t + k]
            np.testing.assert_allclose(dd.P_obs[i, :, k], expect, equal_nan=True)
        assert dd.ref_lp[i].shape == (p.M,)


def test_changing_target_days_does_not_change_features(toy_long):
    p = _panel(toy_long)
    dd = build_decision_data(p, warmup=20)
    i = 50
    t = int(dd.days[i])
    long2 = toy_long.copy()
    long2.loc[long2["date"] >= p.dates[t], "price"] *= 3.0           # alter day t and everything after
    p2 = pn.build_panel(long2, "Tomato", min_reported_days=10)
    dd2 = build_decision_data(p2, warmup=20)
    np.testing.assert_allclose(dd.X[i], dd2.X[i], atol=1e-12)        # features unchanged
    np.testing.assert_allclose(dd.ref_lp[i], dd2.ref_lp[i], atol=1e-12)
    assert not np.allclose(np.nan_to_num(dd.P_obs[i]), np.nan_to_num(dd2.P_obs[i]))   # targets did change


def test_eligibility_uses_only_past_staleness(toy_long):
    p = _panel(toy_long)
    dd = build_decision_data(p, warmup=20)
    st = dd.fs.stale
    for i in (25, 70, 120):
        t = dd.days[i]
        np.testing.assert_array_equal(dd.elig[i], (st[t - 1] <= 14) & ~np.isnan(dd.fs.lp[t - 1]))
