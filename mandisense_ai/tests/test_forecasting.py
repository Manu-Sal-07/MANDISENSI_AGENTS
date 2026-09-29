"""
Tests for the scheduled forecasting system.

Organised around the properties that have to hold for a forecast to be
trustworthy, rather than around code coverage:

  * no realised future value can reach the feature set
  * features never look ahead, and targets resolve on the calendar
  * ingestion is idempotent, so re-running a night cannot double count
  * a series is refused when its history cannot support a forecast
  * a missing or corrupt store degrades instead of breaking a request
"""

import json

import numpy as np
import pandas as pd
import pytest

from mandisense_ai.forecasting.batch_predict import (
    STATUS_DISCONTINUOUS,
    STATUS_REBUILDING,
    STATUS_DORMANT,
    STATUS_INSUFFICIENT_HISTORY,
    STATUS_OK,
    _series_eligibility,
)
from mandisense_ai.forecasting.config import ForecastConfig
from mandisense_ai.forecasting.features import (
    build_features,
    feature_columns,
    is_target_column,
    latest_feature_rows,
)
from mandisense_ai.forecasting.naming import canonical_commodity, canonical_market
from mandisense_ai.forecasting.service import ForecastService
from mandisense_ai.forecasting.store import ForecastStore, ObservationStore


def _config(**overrides):
    base = dict(horizons=(1, 3, 5), min_history_days=30, max_observation_gap_days=21)
    base.update(overrides)
    return ForecastConfig(**base)


def _synthetic_series(n=200, start="2024-01-01", commodity="tomato", mandi="kolar_apmc"):
    """A deterministic daily series with trend, seasonality and noise."""
    rng = np.random.default_rng(7)
    dates = pd.date_range(start, periods=n, freq="D")
    base = 1000 + 150 * np.sin(np.arange(n) * 2 * np.pi / 60)
    price = base + rng.normal(0, 25, n)
    return pd.DataFrame(
        {
            "date": dates,
            "commodity": commodity,
            "mandi_id": mandi,
            "modal_price": price.round(2),
            "arrivals": rng.uniform(50, 150, n).round(1),
            "source": "test",
        }
    )


def _resume_after_break(archive, resumed_on):
    """Append one print long after an archive ends — a series that resumed.

    The row is rebuilt from a dict rather than sliced off the archive:
    `frame.iloc[[-1]]` keeps the parent's datetime block, and concatenating it
    back produces a frame whose `date` column no longer aligns with its rows.
    """
    resumed = pd.DataFrame([{**archive.iloc[-1].to_dict(), "date": resumed_on}])
    return pd.concat([archive, resumed], ignore_index=True)


# ─────────────────────────────── leakage ──────────────────────────────────


class TestTargetLeakage:
    """The defect that produced 0.94 validation skill on a random walk."""

    def test_raw_and_log_targets_are_both_recognised(self):
        assert is_target_column("target_h5")
        assert is_target_column("y_h5")
        assert not is_target_column("price_lag_5")
        assert not is_target_column("roll_mean_7")

    def test_no_target_reaches_the_feature_list(self):
        frame = build_features(_synthetic_series(), _config(), with_targets=True)
        # Mirror what training does: attach log-return targets, then ask for
        # the feature list.
        for horizon in (1, 3, 5):
            frame[f"y_h{horizon}"] = np.log(
                frame[f"target_h{horizon}"] / frame["modal_price"]
            )
        features = feature_columns(frame)
        assert not [name for name in features if name.startswith(("target_h", "y_h"))]

    def test_training_frame_guard_rejects_a_leaked_target(self):
        from mandisense_ai.forecasting.train import _prepare_training_frame

        config = _config()
        frame, features = _prepare_training_frame(_synthetic_series(), config)
        assert features, "expected a usable feature list"
        assert all(not is_target_column(name) for name in features)


# ────────────────────────────── look-ahead ────────────────────────────────


class TestNoLookAhead:
    def test_lags_use_only_past_values(self):
        frame = build_features(_synthetic_series(n=60), _config(), with_targets=False)
        ordered = frame.sort_values("date").reset_index(drop=True)
        # price_lag_1 at row i must equal modal_price at row i-1.
        assert ordered["price_lag_1"].iloc[5] == pytest.approx(
            ordered["modal_price"].iloc[4]
        )

    def test_rolling_mean_excludes_the_current_row(self):
        frame = build_features(_synthetic_series(n=60), _config(), with_targets=False)
        ordered = frame.sort_values("date").reset_index(drop=True)
        expected = ordered["modal_price"].iloc[3:10].mean()
        assert ordered["roll_mean_7"].iloc[10] == pytest.approx(expected, rel=1e-6)

    def test_target_resolves_to_a_future_observation(self):
        frame = build_features(_synthetic_series(n=80), _config(), with_targets=True)
        ordered = frame.sort_values("date").reset_index(drop=True)
        # On a daily series, target_h5 at row i is the price at row i+5.
        assert ordered["target_h5"].iloc[10] == pytest.approx(
            ordered["modal_price"].iloc[15]
        )

    def test_target_is_calendar_based_not_positional(self):
        """
        With a gap in trading, five days ahead still means five calendar days,
        and a target too far past that is withheld rather than faked.
        """
        frame = _synthetic_series(n=40)
        # Drop a stretch so row position and calendar distance diverge.
        frame = frame[~frame["date"].between("2024-01-10", "2024-01-20")]
        built = build_features(frame, _config(), with_targets=True)
        row = built[built["date"] == pd.Timestamp("2024-01-05")].iloc[0]
        # Target date is 10 Jan; the next print is 21 Jan, past the 5-day
        # slack, so no target is assigned.
        assert pd.isna(row["target_h5"])

    def test_target_accepts_a_print_within_horizon_slack(self):
        frame = _synthetic_series(n=40)
        frame = frame[~frame["date"].between("2024-01-10", "2024-01-12")]
        built = build_features(frame, _config(), with_targets=True)
        row = built[built["date"] == pd.Timestamp("2024-01-05")].iloc[0]
        # Target date 10 Jan, next print 13 Jan — inside the slack, so used.
        assert not pd.isna(row["target_h5"])

    def test_latest_rows_are_one_per_series(self):
        frame = pd.concat(
            [
                _synthetic_series(n=50, commodity="tomato"),
                _synthetic_series(n=50, commodity="onion"),
            ]
        )
        latest = latest_feature_rows(frame, _config())
        assert len(latest) == 2
        assert set(latest["commodity"]) == {"tomato", "onion"}


# ────────────────────────── price/arrival elasticity ───────────────────────


class TestPriceArrivalElasticity:
    """
    The rolling log-log price/arrival elasticity feature: the same economic
    signal Stack A's arrival agent computes with a per-row regression fit in
    a Python loop, here as a closed-form rolling covariance/variance ratio.
    """

    def _elastic_series(self, n=120, sign=-1.0):
        """Arrivals and price move in a fixed log-log relationship (sign
        controls direction), so the true elasticity is known and stable."""
        rng = np.random.default_rng(11)
        dates = pd.date_range("2024-01-01", periods=n, freq="D")
        log_arrivals = rng.normal(4.0, 0.3, n)  # around exp(4) ~ 55 tonnes
        log_price = 7.0 + sign * 0.6 * log_arrivals + rng.normal(0, 0.01, n)
        return pd.DataFrame(
            {
                "date": dates,
                "commodity": "tomato",
                "mandi_id": "kolar_apmc",
                "modal_price": np.exp(log_price).round(2),
                "arrivals": np.exp(log_arrivals).round(1),
                "source": "test",
            }
        )

    def test_negative_relationship_is_recovered_with_the_right_sign(self):
        frame = build_features(
            self._elastic_series(sign=-1.0), _config(price_arrival_elasticity_window=30),
            with_targets=False,
        )
        tail = frame.sort_values("date").tail(20)
        assert (tail["price_arrival_elasticity"].dropna() < 0).all()

    def test_positive_relationship_is_recovered_with_the_right_sign(self):
        frame = build_features(
            self._elastic_series(sign=1.0), _config(price_arrival_elasticity_window=30),
            with_targets=False,
        )
        tail = frame.sort_values("date").tail(20)
        assert (tail["price_arrival_elasticity"].dropna() > 0).all()

    def test_short_of_window_is_nan_not_a_noisy_guess(self):
        frame = build_features(
            self._elastic_series(n=15), _config(price_arrival_elasticity_window=30),
            with_targets=False,
        )
        assert frame["price_arrival_elasticity"].iloc[:5].isna().all()

    def test_disabled_arrivals_leave_elasticity_nan(self):
        frame = build_features(
            self._elastic_series(), _config(use_arrivals=False), with_targets=False
        )
        assert frame["price_arrival_elasticity"].isna().all()

    def test_elasticity_is_a_model_feature(self):
        frame = build_features(self._elastic_series(), _config(), with_targets=False)
        assert "price_arrival_elasticity" in feature_columns(frame)

    def test_is_registered_for_arrival_dropout(self):
        """If this ever stops being true, dropout training leaves a real
        arrival-derived signal visible on rows where every other arrival
        feature was masked, quietly defeating the point of the dropout."""
        from mandisense_ai.forecasting.train import ARRIVAL_FEATURES

        assert "price_arrival_elasticity" in ARRIVAL_FEATURES


# ─────────────────────────────── ingestion ────────────────────────────────


class TestObservationStore:
    def test_upsert_is_idempotent(self, tmp_path):
        store = ObservationStore(tmp_path / "obs.parquet")
        records = _synthetic_series(n=30)

        first = store.upsert(records)
        second = store.upsert(records)

        assert first["inserted"] == 30
        assert second["inserted"] == 0
        assert second["total"] == first["total"] == 30

    def test_revised_price_replaces_the_earlier_read(self, tmp_path):
        store = ObservationStore(tmp_path / "obs.parquet")
        records = _synthetic_series(n=5)
        store.upsert(records)

        revised = records.copy()
        revised.loc[revised.index[0], "modal_price"] = 4242.0
        store.upsert(revised)

        stored = store.read().sort_values("date")
        assert stored.iloc[0]["modal_price"] == pytest.approx(4242.0)
        assert len(stored) == 5

    def test_rows_without_a_usable_price_are_dropped(self, tmp_path):
        store = ObservationStore(tmp_path / "obs.parquet")
        records = _synthetic_series(n=5)
        records.loc[records.index[0], "modal_price"] = 0
        records.loc[records.index[1], "modal_price"] = None

        store.upsert(records)
        assert len(store.read()) == 3

    def test_empty_store_reads_as_empty_frame(self, tmp_path):
        assert ObservationStore(tmp_path / "missing.parquet").read().empty


# ────────────────────────────── eligibility ───────────────────────────────


class TestEligibility:
    def _verdict(self, rows, last_days_ago, days_since_prev):
        as_of = pd.Timestamp("2026-09-16")
        return _series_eligibility(
            history_rows=rows,
            last_date=as_of - pd.Timedelta(days=last_days_ago),
            as_of=as_of,
            days_since_prev=days_since_prev,
            config=_config(),
        )

    def test_healthy_series_is_eligible(self):
        assert self._verdict(200, 1, 1.0)["status"] == STATUS_OK

    def test_short_history_is_refused(self):
        verdict = self._verdict(10, 1, 1.0)
        assert verdict["eligible"] is False
        assert verdict["status"] == STATUS_INSUFFICIENT_HISTORY

    def test_dormant_series_is_refused(self):
        verdict = self._verdict(500, 400, 1.0)
        assert verdict["eligible"] is False
        assert verdict["status"] == STATUS_DORMANT

    def test_series_resuming_after_a_long_break_is_refused(self):
        """
        Long history and a print today, but the previous print was months
        ago — every lag feature on that row spans the gap.
        """
        verdict = self._verdict(500, 0, 587.0)
        assert verdict["eligible"] is False
        assert verdict["status"] == STATUS_DISCONTINUOUS

    def test_missing_gap_information_does_not_block(self):
        assert self._verdict(200, 1, None)["status"] == STATUS_OK


# ──────────────────────────────── naming ──────────────────────────────────


class TestNaming:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("Bangarpet APMC", "bangarpet_apmc"),
            ("APMC Akola ", "akola_apmc"),
            ("APMC Pune ", "pune_apmc"),
            ("Hoskote APMC", "hoskote_apmc"),
            ("Kolar", "kolar_apmc"),
            ("Binny Mill (FF&V) Bengaluru APMC", "bangalore_yeshwanthpur"),
        ],
    )
    def test_market_normalisation(self, raw, expected):
        assert canonical_market(raw) == expected

    def test_leading_marker_is_not_duplicated(self):
        assert canonical_market("APMC Mumbai") == "mumbai_apmc"

    def test_distinct_submarkets_stay_distinct(self):
        assert canonical_market("Pune(Pimpri)") != canonical_market("Pune")

    def test_blank_market_returns_none(self):
        assert canonical_market("   ") is None
        assert canonical_market("") is None

    def test_commodity_aliases(self):
        assert canonical_commodity("Tomato") == "tomato"
        assert canonical_commodity("Ginger(Green)") == "ginger"

    @pytest.mark.parametrize(
        "raw",
        [
            "Bangarpet APMC",
            "Binny Mill (FF&V) Bengaluru APMC",
            "bangalore_apmc",
            "bangalore_yeshwanthpur",
            "Kolar",
            "kolar_apmc",
            "Hoskote",
            "lasalgaon",
            "APMC Akola",
        ],
    )
    def test_market_normalisation_is_idempotent(self, raw):
        """Normalising an already-canonical id must be a no-op.

        `bangalore_yeshwanthpur` is the case that broke: it is a canonical id
        that does not end in a market-type word, so a second pass appended
        `_apmc` and produced `bangalore_yeshwanthpur_apmc` — a *different*
        series from the one the cognition layer and the candle API key on.
        Callers re-normalise legitimately (a request path parameter, a
        backfill reading an already-canonical processed dataset), so a rename
        on the second pass silently splits a series' history in two.
        """
        once = canonical_market(raw)
        assert once is not None
        assert canonical_market(once) == once

    def test_phase1_market_ids_resolve_to_store_ids(self):
        """The ids the Phase 1 surfaces use must reach the Phase 2 store.

        The cognition layer addresses Bengaluru as `bangalore_apmc`; the
        observation store keys it as `bangalore_yeshwanthpur`. If this mapping
        ever stops holding, every forecast lookup driven from the UI misses
        and the two halves of the product address disjoint markets.
        """
        assert canonical_market("bangalore_apmc") == "bangalore_yeshwanthpur"
        assert canonical_market("kolar_apmc") == "kolar_apmc"


# ──────────────────────────── store + service ─────────────────────────────


class TestForecastStoreAndService:
    def _store(self):
        return ForecastStore(
            generated_at="2026-09-16T00:00:00+00:00",
            as_of_date="2026-09-15",
            model_version="1.0.0",
            forecasts=[
                {
                    "commodity": "tomato",
                    "mandi_id": "hoskote_apmc",
                    "horizon_days": 3,
                    "status": STATUS_OK,
                    "forecast_price": 1500.0,
                    "last_observed_price": 1480.0,
                },
                {
                    "commodity": "tomato",
                    "mandi_id": "hoskote_apmc",
                    "horizon_days": 5,
                    "status": STATUS_OK,
                    "forecast_price": 1520.0,
                    "last_observed_price": 1480.0,
                },
            ],
            diagnostics={"promoted_horizons": [3, 5]},
        )

    def test_round_trip(self, tmp_path):
        original = self._store()
        path = original.save(tmp_path / "f.json")
        assert ForecastStore.load(path).to_dict() == original.to_dict()

    def test_save_leaves_no_temp_file(self, tmp_path):
        self._store().save(tmp_path / "f.json")
        assert not list(tmp_path.glob("*.tmp"))

    def test_incompatible_schema_is_refused(self, tmp_path):
        payload = self._store().to_dict()
        payload["schema_version"] = "99.0.0"
        path = tmp_path / "f.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(ValueError, match="Incompatible"):
            ForecastStore.load(path)

    def test_curve_is_ordered_by_horizon(self):
        curve = self._store().get("tomato", "hoskote_apmc")
        assert [row["horizon_days"] for row in curve] == [3, 5]

    def test_nearest_horizon_substitutes_sensibly(self, tmp_path):
        path = self._store().save(tmp_path / "f.json")
        service = ForecastService(path)
        # Four days is not published; three is the closest.
        assert service.nearest_horizon("tomato", "hoskote_apmc", 4)["horizon_days"] == 3

    def test_missing_store_degrades_quietly(self, tmp_path):
        service = ForecastService(tmp_path / "absent.json")
        assert service.is_available is False
        assert service.status()["available"] is False
        assert service.get_curve("tomato", "hoskote_apmc") == []
        assert service.get_horizon("tomato", "hoskote_apmc", 5) is None
        assert service.available_series() == []

    def test_corrupt_store_degrades_quietly(self, tmp_path):
        path = tmp_path / "corrupt.json"
        path.write_text("{ not json", encoding="utf-8")
        service = ForecastService(path)
        assert service.is_available is False
        assert "unreadable" in service.status()["reason"]
        assert service.get_curve("tomato", "hoskote_apmc") == []

    def test_reload_picks_up_a_new_store(self, tmp_path):
        path = tmp_path / "f.json"
        service = ForecastService(path)
        assert service.is_available is False

        self._store().save(path)
        assert service.reload() is True
        assert service.is_available is True

    def test_freshness_reports_stale_for_an_old_run(self, tmp_path):
        store = self._store()
        store.generated_at = "2020-01-01T00:00:00+00:00"
        path = store.save(tmp_path / "f.json")
        assert ForecastService(path).freshness() == "STALE"


# ───────────────────────── ingest quality gates ───────────────────────────


class TestIngestValidation:
    """
    A bad price is worse than a missing one: it enters the store and poisons
    every lag and rolling feature that touches it, silently.
    """

    def _rows(self, prices, commodity="tomato", mandi="kolar_apmc"):
        return pd.DataFrame(
            {
                "date": pd.date_range("2026-09-01", periods=len(prices), freq="D"),
                "commodity": commodity,
                "mandi_id": mandi,
                "modal_price": prices,
            }
        )

    def test_plausible_prices_pass(self):
        from mandisense_ai.forecasting.validation import validate_observations

        accepted, report = validate_observations(self._rows([1200, 1350, 1180]))
        assert len(accepted) == 3
        assert report.rejected == 0

    def test_unit_error_is_rejected(self):
        """A price quoted per kilo rather than per quintal."""
        from mandisense_ai.forecasting.validation import (
            REASON_OUT_OF_BOUNDS,
            validate_observations,
        )

        accepted, report = validate_observations(self._rows([1200, 12, 1180]))
        assert len(accepted) == 2
        assert report.reasons[REASON_OUT_OF_BOUNDS] == 1

    def test_fat_finger_is_rejected(self):
        from mandisense_ai.forecasting.validation import (
            REASON_OUT_OF_BOUNDS,
            validate_observations,
        )

        accepted, report = validate_observations(self._rows([1200, 9_999_999]))
        assert len(accepted) == 1
        assert report.reasons[REASON_OUT_OF_BOUNDS] == 1

    def test_spike_against_own_history_is_rejected(self):
        from mandisense_ai.forecasting.validation import (
            REASON_SPIKE,
            validate_observations,
        )

        history = self._rows([1000] * 20)
        # Inside the absolute envelope, but 20x this series' own recent median.
        accepted, report = validate_observations(self._rows([20_000]), history=history)
        assert len(accepted) == 0
        assert report.reasons[REASON_SPIKE] == 1

    def test_real_volatility_is_not_rejected(self):
        """
        Mandi prices genuinely double and halve. The gate must not discard the
        volatility the model exists to forecast.
        """
        from mandisense_ai.forecasting.validation import validate_observations

        history = self._rows([1000] * 20)
        accepted, _ = validate_observations(self._rows([2500, 400]), history=history)
        assert len(accepted) == 2

    def test_spike_gate_abstains_without_enough_history(self):
        from mandisense_ai.forecasting.validation import validate_observations

        accepted, report = validate_observations(
            self._rows([5000]), history=self._rows([1000, 1010])
        )
        assert len(accepted) == 1
        assert report.rejected == 0

    def test_rejections_are_reported_with_reasons(self):
        from mandisense_ai.forecasting.validation import validate_observations

        _, report = validate_observations(self._rows([1200, 5, 9_999_999]))
        payload = report.as_dict()
        assert payload["rejected"] == 2
        assert payload["samples"], "a misbehaving feed must be diagnosable"

    def test_empty_input_is_safe(self):
        from mandisense_ai.forecasting.validation import validate_observations

        accepted, report = validate_observations(pd.DataFrame())
        assert accepted.empty
        assert report.received == 0


# ─────────────────────── windowed inference equivalence ───────────────────


class TestWindowedInference:
    def test_windowing_does_not_change_features(self):
        """
        Inference trims each series to a lookback window for speed. If that
        changed a single feature value it would be train/serve skew, which is
        the exact failure this system is built to avoid.

        The seasonal climatology columns (see `seasonal.py`) are a deliberate,
        documented exception: they need a prior calendar year to reference,
        which a several-month lookback window cannot see by construction —
        that is exactly why serving does not rely on this function to produce
        them and instead overwrites them from the trained bundle's persisted
        climatology table (`batch_predict.generate_forecasts` calls
        `seasonal.lookup_batch` after this function returns). Excluded here
        rather than silently passing, so a real train/serve skew in any other
        column still fails loudly.
        """
        from mandisense_ai.forecasting.features import build_features
        from mandisense_ai.forecasting.seasonal import SEASONAL_FEATURE_COLUMNS

        config = _config()
        long_series = _synthetic_series(n=400)

        full = (
            build_features(long_series, config, with_targets=False)
            .sort_values("date")
            .groupby(["commodity", "mandi_id"], as_index=False)
            .tail(1)
            .reset_index(drop=True)
        )
        windowed = latest_feature_rows(long_series, config)

        columns = [
            c for c in feature_columns(full)
            if c in windowed.columns and c not in SEASONAL_FEATURE_COLUMNS
        ]
        np.testing.assert_allclose(
            full[columns].to_numpy(float),
            windowed[columns].to_numpy(float),
            rtol=1e-9,
            equal_nan=True,
        )


# ──────────────────────── interval calibration ────────────────────────────


class TestIntervalCalibration:
    def test_coverage_classification(self):
        from mandisense_ai.forecasting.backtest import _classify_calibration

        assert _classify_calibration(0.90, 0.90) == "CALIBRATED"
        assert _classify_calibration(0.60, 0.90) == "OVERCONFIDENT"
        assert _classify_calibration(0.99, 0.90) == "CONSERVATIVE"
        assert _classify_calibration(None, 0.90) == "UNKNOWN"

    def test_backtest_reports_out_of_sample_coverage(self):
        """
        Coverage must be measured against a band fit on earlier data, never
        against the residuals the band itself was derived from.
        """
        from mandisense_ai.forecasting.backtest import backtest_horizon
        from mandisense_ai.forecasting.train import _prepare_training_frame

        config = _config(horizons=(3,), min_train_rows=60, walk_forward_folds=2)
        series = pd.concat(
            [
                _synthetic_series(n=600, commodity="tomato"),
                _synthetic_series(n=600, commodity="onion"),
            ]
        )
        frame, features = _prepare_training_frame(series, config)
        result = backtest_horizon(frame, features, 3, config)

        assert result.folds > 0
        assert result.coverage_90 is not None
        assert 0.0 <= result.coverage_90 <= 1.0


class TestReadinessMatchesTheGate:
    """
    The readiness diagnostic is what an operator reads to decide whether a
    missing forecast is a data wait or a pipeline fault. It used to recompute
    eligibility itself and the copy had drifted: it tested history length and
    freshness but not discontinuity, so on the live store 16 series were
    reported READY while the forecaster refused every one of them as
    DISCONTINUOUS_HISTORY. These tests pin readiness to the same function the
    forecast loop gates on.

    With segment-aware features the refusal is now REBUILDING_HISTORY and is
    driven by how many *contiguous* observations back the row, which is the
    same quantity the feature windows are computed over.
    """

    def test_resumed_series_is_not_reported_ready(self):
        from mandisense_ai.forecasting.batch_predict import build_readiness

        config = _config()
        # A long archive that stops, then a single print months later: long
        # enough and recent enough, but every lag on that row reaches back
        # across the break.
        archive = _synthetic_series(n=200, start="2024-01-01")
        observations = _resume_after_break(archive, pd.Timestamp("2026-01-01"))

        report = build_readiness(observations, pd.Timestamp("2026-01-01"), config)
        entry = next(r for r in report if r["mandi_id"] == "kolar_apmc")

        assert entry["state"] == STATUS_REBUILDING
        assert entry["days_since_last"] == 0
        assert entry["segment_observations"] == 1
        assert "1 more needed" not in entry["reason"]
        assert entry["reason"]

    def test_continuous_recent_series_is_ready(self):
        from mandisense_ai.forecasting.batch_predict import build_readiness

        config = _config()
        observations = _synthetic_series(n=200, start="2024-01-01")
        as_of = pd.Timestamp(observations["date"].max())

        entry = build_readiness(observations, as_of, config)[0]
        assert entry["state"] == STATUS_OK
        assert entry["reason"] is None
        assert entry["days_since_previous"] == 1.0

    def test_short_series_still_reports_what_it_is_waiting_for(self):
        from mandisense_ai.forecasting.batch_predict import build_readiness

        config = _config(min_history_days=30)
        observations = _synthetic_series(n=10, start="2026-01-01")
        as_of = pd.Timestamp(observations["date"].max())

        entry = build_readiness(observations, as_of, config)[0]
        assert entry["state"] == STATUS_INSUFFICIENT_HISTORY
        assert entry["observations_remaining"] == 20

    def test_a_single_observation_has_no_previous_gap_to_test(self):
        from mandisense_ai.forecasting.batch_predict import build_readiness

        config = _config(min_history_days=1, min_segment_observations=1)
        observations = _synthetic_series(n=1, start="2026-01-01")

        entry = build_readiness(observations, pd.Timestamp("2026-01-01"), config)[0]
        assert entry["days_since_previous"] is None
        assert entry["segment_observations"] == 1
        assert entry["state"] == STATUS_OK

    def test_readiness_and_the_published_rows_never_disagree(self):
        """
        The property the drift actually violated: for every series the
        forecast loop reached a verdict on, readiness reports that same
        verdict.
        """
        from mandisense_ai.forecasting.batch_predict import build_readiness

        config = _config()
        healthy = _synthetic_series(n=700, start="2024-01-01", mandi="kolar_apmc")

        stale = _synthetic_series(n=200, start="2023-01-01", mandi="hoskote_apmc")

        archive = _synthetic_series(n=200, start="2024-01-01", mandi="agra_apmc")
        broken = _resume_after_break(archive, pd.Timestamp(healthy["date"].max()))

        observations = pd.concat([healthy, stale, broken], ignore_index=True)
        as_of = pd.Timestamp(observations["date"].max())

        states = {
            r["mandi_id"]: r["state"]
            for r in build_readiness(observations, as_of, config)
        }
        assert states["kolar_apmc"] == STATUS_OK
        assert states["hoskote_apmc"] == STATUS_DORMANT
        assert states["agra_apmc"] == STATUS_REBUILDING
