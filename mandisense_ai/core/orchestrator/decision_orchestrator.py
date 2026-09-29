"""
Farmer-facing decision orchestration, served from the validated forecast store.

What this replaced
------------------
This orchestrator used to call `InferenceOrchestrator` (which runs
`inference_engine_v3`) and then `MandiDecisionEngine`, which ran the *same*
inference a second time inside itself — two full model passes per request.
Both read a level-price model whose thresholds (`dir_conf > 0.7`,
`abs_change > 0.05`) were never checked against an outcome; measured against
this project's own per-mandi directional-accuracy table, the 0.7 bar is
unreachable for several mandis, making the SELL branch dead code there.

Meanwhile the forecast store built in the preceding layers — log-return
targets, walk-forward promotion against a naive baseline, empirically
calibrated intervals, and a decision threshold whose SELL/HOLD precision was
actually measured on held-out folds — had exactly one consumer,
`/v1/forecast/*`, and produced no decision anywhere a farmer could see it.
Comparing the two for the same ten series, three disagreed on direction. A
farmer and a trader looking at the same mandi on the same day got opposite
calls.

This now reads the published store, so every surface answers from one source.

Two consequences worth stating plainly:

**The horizon is finally honoured.** `query_parser` has always extracted
"after 15 days" correctly and the old path then discarded it, so every
question got the same answer regardless of when the farmer intended to sell.
Horizons are resolved against what was actually published, and a substitution
is reported rather than hidden — a 15-day question answered from the 7-day
model says so.

**A series with no publishable forecast says so.** Insufficient history,
dormancy and a discontinuous series are real states the store already
distinguishes. Falling back to the legacy engine for those rows would
reintroduce exactly the contradictions this change removes, so the honest
status is returned instead.
"""

from typing import Any, Dict, Optional

from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

# Descriptive bucketing of a *measured* quantity (the calibrated 90% band
# width as a share of price), used only to fill the legacy `risk_level` and
# `signal_strength` strings that existing callers read. These are labels on a
# number, not thresholds that decide anything — the decision itself comes
# from `decision.py`'s backtested threshold. `interval_width_pct` and
# `probability_of_decline` are passed through untouched so any consumer can
# use the measured values rather than these buckets.
_WIDE_BAND_PCT = 25.0
_NARROW_BAND_PCT = 15.0
_STRONG_MOVE_PCT = 5.0
_MODERATE_MOVE_PCT = 2.0

SUPPORTED_ACTIONS = ("SELL", "HOLD", "WAIT")


def _risk_from_band_width(width_pct: Optional[float]) -> str:
    if width_pct is None:
        return "UNKNOWN"
    if width_pct >= _WIDE_BAND_PCT:
        return "HIGH"
    if width_pct <= _NARROW_BAND_PCT:
        return "LOW"
    return "MEDIUM"


def _strength_from_move(change_pct: Optional[float]) -> str:
    if change_pct is None:
        return "UNKNOWN"
    magnitude = abs(change_pct)
    if magnitude >= _STRONG_MOVE_PCT:
        return "STRONG"
    if magnitude >= _MODERATE_MOVE_PCT:
        return "MODERATE"
    return "WEAK"


def _band_width_pct(row: Dict[str, Any]) -> Optional[float]:
    interval = row.get("interval") or {}
    low, high = interval.get("p05"), interval.get("p95")
    base = row.get("last_observed_price")
    if low is None or high is None or not base:
        return None
    return float((high - low) / base * 100.0)


def _build_reasoning(
    commodity: str,
    mandi_id: str,
    row: Dict[str, Any],
    requested_horizon: Optional[int],
    width_pct: Optional[float],
) -> str:
    horizon = row.get("horizon_days")
    change = row.get("expected_change_pct")
    decision = row.get("decision") or "WAIT"
    probability = row.get("decision_probability_of_decline")
    interval = row.get("interval") or {}

    place = mandi_id.replace("_apmc", "").replace("_", " ").title()
    parts = []

    if change is not None and horizon:
        movement = "rise" if change > 0 else "fall" if change < 0 else "stay flat"
        parts.append(
            f"In {place}, {commodity} is forecast to {movement} "
            f"{abs(float(change)):.1f}% over the next {horizon} day(s)."
        )

    if interval.get("p05") is not None and interval.get("p95") is not None:
        parts.append(
            f"The 90% range is Rs {interval['p05']:,.0f} to Rs {interval['p95']:,.0f}"
            + (f" (a {width_pct:.0f}% band)." if width_pct is not None else ".")
        )

    if probability is not None:
        if decision == "SELL":
            parts.append(f"A decline is the more likely outcome ({probability:.0%} chance).")
        elif decision == "HOLD":
            parts.append(f"A rise is the more likely outcome ({1 - probability:.0%} chance).")
        else:
            parts.append(
                f"Neither direction is confident enough to act on "
                f"({probability:.0%} chance of a decline), so waiting is safer."
            )

    # A substituted horizon is stated, never silently swapped.
    if requested_horizon and horizon and int(requested_horizon) != int(horizon):
        parts.append(
            f"You asked about {requested_horizon} days; the nearest published "
            f"forecast is {horizon} days, so that is what this is based on."
        )

    skill = row.get("model_skill")
    if skill is not None:
        parts.append(
            f"This model beats a no-change forecast by {float(skill) * 100:.0f}% "
            "on held-out history."
        )

    return " ".join(parts) if parts else "No forecast detail is available for this series."


# ── call taxonomy ──────────────────────────────────────────────────────────
#
# Three epistemically different outcomes used to render identically as the
# word "WAIT", which is the last-mile failure that undoes the rest of this
# system: a farmer could not tell a validated "hold your crop" from "we have
# no forecast for this crop at all".
#
#   ADVISED      a directional call, made because a threshold whose precision
#                was measured on held-out folds was cleared
#   ABSTAINED    a forecast exists and the policy declined to call it -- the
#                model ran and said "not confident enough", which is a real
#                and useful answer
#   UNAVAILABLE  there is no forecast for this series at all, so nothing was
#                decided and nothing should be implied
#
# Carried end-to-end rather than re-derived per surface, so no screen can
# quietly collapse them back together again.
CALL_ADVISED = "ADVISED"
CALL_ABSTAINED = "ABSTAINED"
CALL_UNAVAILABLE = "UNAVAILABLE"

# Why the policy abstained, when it did. These are not interchangeable: the
# first says this particular row was too close to call, the second says the
# horizon never earned a threshold at all and *no* row of it will be called.
ABSTAIN_UNCERTAIN = "PROBABILITY_IN_UNCERTAIN_BAND"
ABSTAIN_NO_THRESHOLD = "NO_VALIDATED_THRESHOLD"


def _unavailable(commodity: str, mandi_id: str, status: str, reason: str) -> Dict[str, Any]:
    """An honest refusal, in the shape existing callers already handle."""
    return {
        "commodity": commodity,
        "mandi_id": mandi_id,
        "decision": "WAIT",
        "call_type": CALL_UNAVAILABLE,
        "abstention_reason": None,
        "status": status,
        "reason": reason,
        "confidence": 0.0,
        "risk_level": "UNKNOWN",
        "signal_strength": "UNKNOWN",
        "price_change_pct": 0.0,
        "reasoning": reason,
        "raw_inference": {},
    }


class DecisionOrchestrator:
    """Reads the published forecast store; runs no model at request time."""

    async def get_actionable_decision(
        self,
        commodity: str,
        mandi_id: str,
        horizon_days: Optional[int] = None,
    ) -> Dict[str, Any]:
        from mandisense_ai.forecasting.naming import canonical_commodity, canonical_market
        from mandisense_ai.forecasting.service import get_forecast_service

        try:
            service = get_forecast_service()
            if not service.is_available:
                status = service.status()
                return _unavailable(
                    commodity, mandi_id, "FORECAST_UNAVAILABLE",
                    f"No published forecast yet ({status.get('reason', 'unknown')}). "
                    "The nightly job has not produced one.",
                )

            resolved_commodity = canonical_commodity(commodity) or str(commodity).strip().lower()
            resolved_mandi = canonical_market(mandi_id) or str(mandi_id).strip().lower()

            curve = service.get_curve(resolved_commodity, resolved_mandi)
            if not curve:
                return _unavailable(
                    commodity, mandi_id, "NOT_TRACKED",
                    f"{commodity} at {mandi_id} is not a tracked series in the "
                    "current forecast store.",
                )

            # Honour the asked-for horizon; fall back to the nearest published
            # one and record the substitution so `_build_reasoning` can say so.
            row = None
            if horizon_days:
                row = service.get_horizon(resolved_commodity, resolved_mandi, int(horizon_days))
                if row is None:
                    row = service.nearest_horizon(resolved_commodity, resolved_mandi, int(horizon_days))
            if row is None:
                row = curve[0]

            if row.get("status") != "OK":
                return _unavailable(
                    commodity, mandi_id, row.get("status", "UNAVAILABLE"),
                    row.get("reason") or "This series cannot be forecast right now.",
                )

            decision = row.get("decision")
            if decision not in SUPPORTED_ACTIONS:
                # The store published a forecast but the decision policy has
                # not been calibrated for this horizon yet (no threshold
                # cleared its precision bar, or the bundle predates the
                # policy). WAIT is the honest answer, with the reason kept.
                abstention_reason = ABSTAIN_NO_THRESHOLD
                decision = "WAIT"
            elif decision == "WAIT":
                # A calibrated policy ran on this row and declined to call it.
                abstention_reason = ABSTAIN_UNCERTAIN
            else:
                abstention_reason = None

            call_type = CALL_ABSTAINED if decision == "WAIT" else CALL_ADVISED

            probability = row.get("decision_probability_of_decline")
            # Confidence is the probability of the direction actually being
            # called — a calibrated number, not a separate invented score.
            if probability is None:
                confidence = 0.0
            elif decision == "SELL":
                confidence = float(probability)
            elif decision == "HOLD":
                confidence = 1.0 - float(probability)
            else:
                confidence = max(float(probability), 1.0 - float(probability))

            width_pct = _band_width_pct(row)
            change_pct = row.get("expected_change_pct")

            return {
                "commodity": resolved_commodity,
                "mandi_id": resolved_mandi,
                "decision": decision,
                "call_type": call_type,
                "abstention_reason": abstention_reason,
                "status": "OK",
                "reason": None,
                "confidence": round(confidence, 4),
                "risk_level": _risk_from_band_width(width_pct),
                "signal_strength": _strength_from_move(change_pct),
                "price_change_pct": float(change_pct) if change_pct is not None else 0.0,
                "horizon_days": row.get("horizon_days"),
                "requested_horizon_days": horizon_days,
                "target_date": row.get("target_date"),
                "interval": row.get("interval"),
                "interval_width_pct": round(width_pct, 2) if width_pct is not None else None,
                "probability_of_decline": probability,
                "interval_source": row.get("interval_source"),
                "prediction_source": row.get("prediction_source"),
                "model_skill": row.get("model_skill"),
                "as_of_date": row.get("as_of_date"),
                "data_lag_days": row.get("data_lag_days"),
                "freshness": service.freshness(),
                "reasoning": _build_reasoning(
                    resolved_commodity, resolved_mandi, row, horizon_days, width_pct
                ),
                # Kept for the discovery detail view, which reads these two.
                "raw_inference": {
                    "predicted_price": row.get("forecast_price"),
                    "arrival_signal": "unavailable",
                },
            }
        except Exception as exc:
            logger.error(
                "Decision lookup failed for %s/%s: %s", commodity, mandi_id, exc, exc_info=True
            )
            return _unavailable(
                commodity, mandi_id, "ERROR",
                "The forecast service could not be read for this series.",
            )
