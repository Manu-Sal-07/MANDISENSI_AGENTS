"""
Objectives 1 and 4 — the ensemble's feedback and volatility loop.

The multi-agent ensemble does not use fixed weights: it logs each model's
prediction, learns the realised error once the outcome is known, and
re-weights from that rolling error plus the detected volatility regime. That
loop is the "volatility system for feedback", and until now it was the
least-covered code in the project — `feedback_store`, `dynamic_weighter`,
`prediction_logger` and `regime_detector` sat between 22% and 25%.

Low coverage there is not a cosmetic gap. A feedback loop fails *quietly*:
weights that stop responding, or a store that silently writes somewhere the
reader never looks, produce a system that still returns numbers and simply
stops learning. That exact failure was present — both stores resolved their
path relative to the process working directory, so the history split across
two directories and the rolling error was computed from roughly half of it.
`TestStorageLocation` exists to keep it fixed.

Every test writes to a `tmp_path` store, so the suite never reads or mutates
the real prediction history.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

import pandas as pd
import pytest

from mandisense_ai.ensemble.dynamic_weighter import DynamicWeighter
from mandisense_ai.ensemble.feedback_store import FeedbackStore, default_ensemble_dir
from mandisense_ai.ensemble.regime_detector import RegimeDetector


@pytest.fixture
def store(tmp_path) -> FeedbackStore:
    return FeedbackStore(storage_dir=tmp_path / "ensemble")


def _log(store: FeedbackStore, model: str, prediction: float, actual=None, **kw):
    store.log_prediction(
        agent_type=kw.get("agent_type", "Seasonality"),
        commodity=kw.get("commodity", "tomato"),
        mandi=kw.get("mandi", "kolar_apmc"),
        model_name=model,
        target_date=kw.get("target_date", "2026-05-02"),
        prediction=prediction,
        actual=actual,
    )


# ───────────────────────── storage location ──────────────────────────


class TestStorageLocation:
    """Regression cover for the split-history bug."""

    def test_default_directory_is_absolute(self):
        """A relative default makes the store follow the working directory."""
        assert default_ensemble_dir().is_absolute()

    def test_default_location_is_independent_of_cwd(self, tmp_path, monkeypatch):
        before = FeedbackStore().file_path
        monkeypatch.chdir(tmp_path)
        after = FeedbackStore().file_path
        assert before == after

    def test_logger_and_store_share_one_directory(self):
        """Two halves of one history must not live in two places."""
        from mandisense_ai.ensemble.prediction_logger import PredictionLogger

        assert PredictionLogger().file_path.parent == FeedbackStore().file_path.parent

    def test_explicit_directory_is_honoured(self, tmp_path):
        store = FeedbackStore(storage_dir=tmp_path / "custom")
        assert store.file_path.parent == tmp_path / "custom"


# ───────────────────────── logging + error ───────────────────────────


class TestFeedbackStore:
    def test_prediction_is_persisted(self, store):
        _log(store, "XGBoost", 1500.0)
        lines = store.file_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["model_name"] == "XGBoost"

    def test_error_is_computed_when_actual_is_known(self, store):
        _log(store, "XGBoost", 1100.0, actual=1000.0)
        record = json.loads(store.file_path.read_text(encoding="utf-8").strip())
        assert record["error"] == pytest.approx(0.10)

    def test_error_is_absolute_not_signed(self, store):
        """An under-prediction and an over-prediction are equally wrong."""
        _log(store, "Under", 900.0, actual=1000.0)
        _log(store, "Over", 1100.0, actual=1000.0)
        errors = [
            json.loads(line)["error"]
            for line in store.file_path.read_text(encoding="utf-8").splitlines()
        ]
        assert all(e > 0 for e in errors)
        assert errors[0] == pytest.approx(errors[1])

    def test_zero_actual_does_not_divide_by_zero(self, store):
        _log(store, "XGBoost", 1500.0, actual=0.0)
        record = json.loads(store.file_path.read_text(encoding="utf-8").strip())
        assert record["error"] is None

    def test_pending_prediction_has_no_error_yet(self, store):
        _log(store, "XGBoost", 1500.0)
        record = json.loads(store.file_path.read_text(encoding="utf-8").strip())
        assert record["actual"] is None
        assert record["error"] is None

    def test_actuals_backfill_computes_error(self, store):
        _log(store, "XGBoost", 1100.0)
        store.update_actuals(
            agent_type="Seasonality",
            commodity="tomato",
            mandi="kolar_apmc",
            target_date="2026-05-02",
            actual=1000.0,
        )
        record = json.loads(store.file_path.read_text(encoding="utf-8").strip())
        assert record["actual"] == 1000.0
        assert record["error"] == pytest.approx(0.10)

    def test_backfill_does_not_overwrite_a_known_actual(self, store):
        _log(store, "XGBoost", 1100.0, actual=1000.0)
        store.update_actuals(
            agent_type="Seasonality",
            commodity="tomato",
            mandi="kolar_apmc",
            target_date="2026-05-02",
            actual=5000.0,
        )
        record = json.loads(store.file_path.read_text(encoding="utf-8").strip())
        assert record["actual"] == 1000.0

    def test_backfill_leaves_other_series_untouched(self, store):
        _log(store, "XGBoost", 1100.0, commodity="tomato")
        _log(store, "XGBoost", 900.0, commodity="onion")
        store.update_actuals(
            agent_type="Seasonality",
            commodity="tomato",
            mandi="kolar_apmc",
            target_date="2026-05-02",
            actual=1000.0,
        )
        records = [
            json.loads(line)
            for line in store.file_path.read_text(encoding="utf-8").splitlines()
        ]
        by_commodity = {r["commodity"]: r for r in records}
        assert by_commodity["tomato"]["actual"] == 1000.0
        assert by_commodity["onion"]["actual"] is None

    def test_rolling_mape_on_empty_store_is_none(self, store):
        assert (
            store.get_rolling_mape("Seasonality", "tomato", "kolar_apmc", "XGBoost")
            is None
        )

    def test_rolling_mape_averages_scored_records(self, store):
        _log(store, "XGBoost", 1100.0, actual=1000.0)  # 0.10
        _log(store, "XGBoost", 1200.0, actual=1000.0)  # 0.20
        mape = store.get_rolling_mape(
            "Seasonality", "tomato", "kolar_apmc", "XGBoost"
        )
        assert mape == pytest.approx(0.15)

    def test_rolling_mape_isolates_model(self, store):
        _log(store, "XGBoost", 1100.0, actual=1000.0)
        _log(store, "Ridge", 2000.0, actual=1000.0)
        assert store.get_rolling_mape(
            "Seasonality", "tomato", "kolar_apmc", "XGBoost"
        ) == pytest.approx(0.10)

    def test_rolling_mape_isolates_series(self, store):
        _log(store, "XGBoost", 1100.0, actual=1000.0, commodity="tomato")
        _log(store, "XGBoost", 3000.0, actual=1000.0, commodity="onion")
        assert store.get_rolling_mape(
            "Seasonality", "tomato", "kolar_apmc", "XGBoost"
        ) == pytest.approx(0.10)

    def test_unscored_records_do_not_enter_the_average(self, store):
        _log(store, "XGBoost", 1100.0, actual=1000.0)
        _log(store, "XGBoost", 9999.0)  # still pending
        assert store.get_rolling_mape(
            "Seasonality", "tomato", "kolar_apmc", "XGBoost"
        ) == pytest.approx(0.10)


# ───────────────────────── dynamic weighting ─────────────────────────


class TestDynamicWeighter:
    """Objective 4: weights must actually move with measured error."""

    def test_weights_sum_to_one(self, store):
        weighter = DynamicWeighter(store)
        weights = weighter.adjust_weights(
            {"XGBoost": 0.5, "Ridge": 0.5},
            "Seasonality",
            "tomato",
            "kolar_apmc",
            regimes={},
        )
        assert sum(weights.values()) == pytest.approx(1.0)

    def test_empty_base_weights_return_empty(self, store):
        assert DynamicWeighter(store).adjust_weights(
            {}, "Seasonality", "tomato", "kolar_apmc", regimes={}
        ) == {}

    def test_no_history_leaves_weights_unchanged(self, store):
        weights = DynamicWeighter(store).adjust_weights(
            {"XGBoost": 0.5, "Ridge": 0.5},
            "Seasonality",
            "tomato",
            "kolar_apmc",
            regimes={},
        )
        assert weights["XGBoost"] == pytest.approx(0.5)
        assert weights["Ridge"] == pytest.approx(0.5)

    def test_the_more_accurate_model_gains_weight(self, store):
        """The loop's whole purpose, stated as an assertion."""
        for _ in range(3):
            _log(store, "Accurate", 1010.0, actual=1000.0)  # 1% error
            _log(store, "Inaccurate", 1400.0, actual=1000.0)  # 40% error

        weights = DynamicWeighter(store).adjust_weights(
            {"Accurate": 0.5, "Inaccurate": 0.5},
            "Seasonality",
            "tomato",
            "kolar_apmc",
            regimes={},
        )
        assert weights["Accurate"] > weights["Inaccurate"]

    def test_festival_regime_boosts_its_models(self, store):
        weighter = DynamicWeighter(store)
        base = {"SARIMA": 0.5, "Ridge": 0.5}

        flat = weighter.adjust_weights(
            base, "Seasonality", "tomato", "kolar_apmc", regimes={}
        )
        boosted = weighter.adjust_weights(
            base, "Seasonality", "tomato", "kolar_apmc", regimes={"festival": True}
        )
        assert boosted["SARIMA"] > flat["SARIMA"]

    def test_supply_shock_regime_boosts_its_models(self, store):
        weighter = DynamicWeighter(store)
        base = {"GradientBoosting": 0.5, "Ridge": 0.5}

        flat = weighter.adjust_weights(
            base, "Seasonality", "tomato", "kolar_apmc", regimes={}
        )
        boosted = weighter.adjust_weights(
            base, "Seasonality", "tomato", "kolar_apmc", regimes={"supply_shock": True}
        )
        assert boosted["GradientBoosting"] > flat["GradientBoosting"]

    def test_boost_is_still_normalised(self, store):
        weights = DynamicWeighter(store).adjust_weights(
            {"SARIMA": 0.5, "Ridge": 0.5},
            "Seasonality",
            "tomato",
            "kolar_apmc",
            regimes={"festival": True},
        )
        assert sum(weights.values()) == pytest.approx(1.0)

    def test_alpha_controls_responsiveness(self, store):
        """A higher EMA alpha must react harder to recent error."""
        for _ in range(3):
            _log(store, "Accurate", 1010.0, actual=1000.0)
            _log(store, "Inaccurate", 1400.0, actual=1000.0)

        base = {"Accurate": 0.5, "Inaccurate": 0.5}
        sluggish = DynamicWeighter(store, alpha=0.05).adjust_weights(
            base, "Seasonality", "tomato", "kolar_apmc", regimes={}
        )
        responsive = DynamicWeighter(store, alpha=0.9).adjust_weights(
            base, "Seasonality", "tomato", "kolar_apmc", regimes={}
        )
        assert responsive["Accurate"] > sluggish["Accurate"]


# ───────────────────────── regime detection ──────────────────────────


class TestRegimeDetector:
    """The volatility signal the weighting reacts to."""

    def _frame(self, prices, festival=0) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "modal_price": prices,
                "arrivals_tonnes": [100.0] * len(prices),
                "is_festival": [festival] * len(prices),
            }
        )

    def test_too_little_data_claims_no_regime(self):
        result = RegimeDetector().detect_regime(self._frame([100.0, 101.0]))
        assert result == {
            "high_volatility": False,
            "festival": False,
            "supply_shock": False,
        }

    def test_empty_frame_is_safe(self):
        assert RegimeDetector().detect_regime(pd.DataFrame())["high_volatility"] is False

    def test_flat_prices_are_not_volatile(self):
        result = RegimeDetector().detect_regime(self._frame([1000.0] * 20))
        assert result["high_volatility"] is False

    def test_swinging_prices_are_volatile(self):
        prices = [1000.0 if i % 2 == 0 else 1400.0 for i in range(20)]
        assert RegimeDetector().detect_regime(self._frame(prices))["high_volatility"]

    def test_festival_flag_is_detected(self):
        result = RegimeDetector().detect_regime(self._frame([1000.0] * 20, festival=1))
        assert result["festival"] is True

    def test_threshold_is_respected(self):
        """A detector whose threshold does nothing is not a detector."""
        prices = [1000.0 if i % 2 == 0 else 1050.0 for i in range(20)]
        frame = self._frame(prices)
        assert RegimeDetector(volatility_threshold=0.001).detect_regime(frame)[
            "high_volatility"
        ]
        assert not RegimeDetector(volatility_threshold=0.9).detect_regime(frame)[
            "high_volatility"
        ]
