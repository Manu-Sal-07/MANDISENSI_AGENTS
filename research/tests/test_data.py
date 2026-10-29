import numpy as np
import pandas as pd
import pytest

from gfmc.data import loader, panel, registry


def test_history_loader_real_file_contract():
    long, rep = loader.load_history()
    assert rep.footer_rows_dropped >= 1                 # the portal's "Note:" lines are removed
    assert rep.unparseable_dates == 0
    assert long["price"].gt(0).all()
    assert not long.duplicated(["date", "market", "commodity"]).any()
    assert set(long["source"]) == {"agmarknet_all_type_report"}
    assert {"Tomato", "Onion", "Potato"} <= set(long["commodity"])


def test_daily_loader_aggregates_to_market_day():
    daily, rep = loader.load_daily_reports()
    assert not daily.duplicated(["date", "market", "commodity"]).any()
    assert (daily["price"] >= daily["min_price"] - 1e-9).all()
    assert (daily["price"] <= daily["max_price"] + 1e-9).all()


def test_sources_agree_where_they_overlap():
    hist, _ = loader.load_history()
    daily, _ = loader.load_daily_reports()
    chk = loader.crosscheck_sources(hist, daily, "Tomato")
    assert chk["overlap_rows"] > 500
    assert chk["pearson_r"] > 0.95                      # same underlying portal data


def test_units_guard():
    bad = pd.DataFrame({"p": ["Rs./Kg"], "a": ["Metric Tonnes"]})
    with pytest.raises(loader.DataError):
        loader._check_units(bad, "p", "a")


def test_panel_mask_matches_missing(toy_long):
    pan = panel.build_panel(toy_long, "Tomato", min_reported_days=10)
    assert pan.price.shape == (pan.T, pan.M)
    assert (pan.mask == ~np.isnan(pan.price)).all()
    assert pan.T == 200                                  # every calendar day is present


def test_staleness_semantics(toy_long):
    pan = panel.build_panel(toy_long, "Tomato", min_reported_days=10)
    st = panel.staleness(pan.mask)
    assert (st[pan.mask] == 0).all()                     # 0 exactly on reported days
    j = 0
    t = int(np.flatnonzero(~pan.mask[:, j])[0])
    assert st[t, j] == st[t - 1, j] + 1 or st[t - 1, j] == 60


def test_ffill_never_creates_values_before_first_report():
    p = np.array([[np.nan], [np.nan], [10.0], [np.nan], [12.0]])
    f = panel.ffill_price(p)
    assert np.isnan(f[0, 0]) and np.isnan(f[1, 0])
    assert f[3, 0] == 10.0


def test_distance_is_symmetric_and_positive():
    a, b = registry.ORIGINS["Kolar"], registry.ORIGINS["Bengaluru"]
    assert registry.haversine_km(a, b) == pytest.approx(registry.haversine_km(b, a))
    assert 50 < registry.haversine_km(a, b) < 80


def test_unknown_market_fails_loudly():
    with pytest.raises(KeyError):
        registry.coords("Nowhere APMC")
