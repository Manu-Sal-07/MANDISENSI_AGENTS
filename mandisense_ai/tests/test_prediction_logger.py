"""
Objective 4 — the append-only prediction log.

This is the training substrate for the learned ensemble: every meta-ensemble
cycle is written here, outcomes are backfilled once the horizon elapses, and
only backfilled records become training-eligible.

The property worth protecting is the leakage boundary. A record whose outcome
is not yet known must never reach training, because a model trained on
`actual = null` coerced to zero learns that every prediction was perfect. The
separation is enforced by `read_completed`, so that is what these tests pin
down, alongside the append-only guarantee that makes concurrent runners safe.
"""

from __future__ import annotations

import json

import pytest

from mandisense_ai.ensemble.prediction_logger import PredictionLogger


@pytest.fixture
def logger(tmp_path) -> PredictionLogger:
    return PredictionLogger(storage_dir=tmp_path / "ensemble")


def _log(logger: PredictionLogger, commodity="tomato", mandi="kolar_apmc", pred=1500.0):
    return logger.log_prediction(
        commodity=commodity,
        mandi=mandi,
        seasonality_pred_30d=pred,
        seasonality_confidence=0.8,
        seasonality_volatility=0.2,
        seasonality_regime="STABLE",
        arrival_pred_7d=120.0,
        arrival_confidence=0.7,
        arrival_supply_stress=0.3,
        arrival_regime="NORMAL",
        external_impact=0.05,
        external_confidence=0.6,
        phase1_prediction=pred,
        phase1_confidence=0.75,
        phase1_conflict=False,
        phase1_strong_conflict=False,
    )


class TestAppendOnly:
    def test_record_id_is_returned_and_unique(self, logger):
        first, second = _log(logger), _log(logger)
        assert first and second and first != second

    def test_writes_are_append_only(self, logger):
        """Rewriting in place would corrupt a concurrent runner's view."""
        _log(logger)
        first_pass = logger.file_path.read_text(encoding="utf-8")
        _log(logger)
        second_pass = logger.file_path.read_text(encoding="utf-8")

        assert second_pass.startswith(first_pass)
        assert len(second_pass) > len(first_pass)

    def test_each_record_is_one_json_line(self, logger):
        _log(logger)
        _log(logger)
        lines = [
            line
            for line in logger.file_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert len(lines) == 2
        for line in lines:
            json.loads(line)  # must parse standalone - the file is streamable

    def test_outcome_starts_null(self, logger):
        _log(logger)
        record = json.loads(logger.file_path.read_text(encoding="utf-8").strip())
        assert record["actual_7d_change"] is None


class TestReads:
    def test_read_all_returns_every_record(self, logger):
        _log(logger)
        _log(logger)
        assert len(logger.read_all()) == 2

    def test_read_all_on_missing_file_is_empty(self, tmp_path):
        assert PredictionLogger(storage_dir=tmp_path / "empty").read_all() == []

    def test_pending_records_are_not_training_eligible(self, logger):
        """The leakage boundary."""
        _log(logger)
        assert logger.read_all() != []
        assert logger.read_completed() == []

    def test_count_filters_by_series(self, logger):
        _log(logger, commodity="tomato")
        _log(logger, commodity="onion")
        assert logger.count_records() == 2
        assert logger.count_records(commodity="tomato") == 1


class TestBackfill:
    def test_backfill_marks_record_complete(self, logger):
        _log(logger)
        record = logger.read_all()[0]

        updated = logger.backfill_actual(
            commodity="tomato",
            mandi="kolar_apmc",
            target_timestamp=record["timestamp"],
            actual_7d_change=0.05,
        )

        assert updated == 1
        completed = logger.read_completed()
        assert len(completed) == 1
        assert completed[0]["actual_7d_change"] == 0.05

    def test_backfill_leaves_other_series_pending(self, logger):
        _log(logger, commodity="tomato")
        _log(logger, commodity="onion")
        timestamp = logger.read_all()[0]["timestamp"]

        logger.backfill_actual(
            commodity="tomato",
            mandi="kolar_apmc",
            target_timestamp=timestamp,
            actual_7d_change=0.05,
        )

        completed = logger.read_completed()
        assert [r["commodity"] for r in completed] == ["tomato"]

    def test_backfill_with_no_match_changes_nothing(self, logger):
        _log(logger)
        updated = logger.backfill_actual(
            commodity="nonexistent",
            mandi="nowhere",
            target_timestamp="2020-01-01T00:00:00",
            actual_7d_change=0.05,
        )
        assert updated == 0
        assert logger.read_completed() == []

    def test_record_count_is_preserved_across_backfill(self, logger):
        """A rewrite that drops rows would silently shrink the training set."""
        _log(logger)
        _log(logger, commodity="onion")
        before = logger.count_records()

        logger.backfill_actual(
            commodity="tomato",
            mandi="kolar_apmc",
            target_timestamp=logger.read_all()[0]["timestamp"],
            actual_7d_change=0.05,
        )

        assert logger.count_records() == before

    def test_completed_only_count_tracks_backfill(self, logger):
        _log(logger)
        assert logger.count_records(completed_only=True) == 0

        logger.backfill_actual(
            commodity="tomato",
            mandi="kolar_apmc",
            target_timestamp=logger.read_all()[0]["timestamp"],
            actual_7d_change=0.05,
        )

        assert logger.count_records(completed_only=True) == 1
