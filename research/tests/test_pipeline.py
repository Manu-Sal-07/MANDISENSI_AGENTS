"""End-to-end pipeline test on the real data with a tiny budget (one fold, two cheap models)."""

import numpy as np
import pytest

from gfmc import experiment
from gfmc.analysis import Study
from gfmc.config import Conformal


@pytest.fixture(scope="module")
def tiny_study(tmp_path_factory):
    cache = tmp_path_factory.mktemp("cache")
    mp = pytest.MonkeyPatch()
    mp.setattr(experiment, "CACHE_DIR", cache)
    experiment.run_task("rw", 4, "Tomato", 0, 1, cache=False)
    experiment.run_task("lgbm_filled", 4, "Tomato", 2, 1, cache=False)
    yield Study("Tomato", specs=["rw", "lgbm_filled"], folds=[4])
    mp.undo()


def test_walk_forward_plan_has_no_overlap(tiny_study):
    pl = tiny_study.plans[4]
    d = tiny_study.dd.dates
    assert d[pl.train_idx].max() < d[pl.test_idx].min() - np.timedelta64(experiment.GAP_DAYS - 1, "D")
    assert d[pl.calib_train_idx].max() < d[pl.calib_idx].min()
    assert d[pl.calib_idx].max() < d[pl.test_idx].min()
    assert set(pl.calib_idx).isdisjoint(pl.test_idx)


def test_main_table_is_internally_consistent(tiny_study):
    t = tiny_study.main_table().set_index("method")
    oracle = t.loc["oracle(hindsight)", "revenue"]
    for m in ("rw", "lgbm_filled", "nearest_today", "highest_yesterday", "farm_gate"):
        assert t.loc[m, "revenue"] <= oracle + 1e-6
        assert t.loc[m, "rev_ci_lo"] <= t.loc[m, "revenue"] <= t.loc[m, "rev_ci_hi"]
    assert 0 <= t.loc["lgbm_filled", "fallback_rate"] <= 1


def test_floor_policy_is_scored_out_of_sample_only(tiny_study):
    r = tiny_study.floor_run("lgbm_filled", Conformal(alpha=0.10, gamma=0.01))
    assert len(r["floor"]) == len(tiny_study.plans[4].test_idx)
    assert 0.0 <= r["violation"] <= 0.5
    assert np.isfinite(r["floor"]).all()


def test_forecast_table_has_random_walk_at_zero_skill(tiny_study):
    t = tiny_study.forecast_table().set_index("method")
    assert t.loc["rw", "skill_vs_rw_observed"] == pytest.approx(0.0, abs=1e-12)
