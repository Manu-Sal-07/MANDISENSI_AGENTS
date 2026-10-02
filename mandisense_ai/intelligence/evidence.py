"""
Evidence assembly.

Gathers everything the system actually knows about one (commodity, mandi)
into a flat, keyed bundle before any model is called.

Two properties matter and both are deliberate.

**Flat and keyed.** Every fact is addressable — `forecast.h5.point`,
`cognition.decision`, `spillover.evidence_state`. The model is told to cite
these keys, and `grounding.py` walks the same keys to check the numbers it
returned. A nested blob would make both impossible.

**Complete or explicitly absent.** A source that is unavailable is recorded
as unavailable with a reason, never omitted. An omitted source is
indistinguishable from a source that reported nothing, and the model would
be free to assume whichever suited its answer.

Nothing in this module calls a model, and nothing raises: a brief built on
partial evidence is useful, a 500 is not.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class EvidenceBundle:
    commodity: str
    mandi_id: str
    assembled_at: str
    facts: Dict[str, Any] = field(default_factory=dict)
    """Flat key -> value. Keys are dotted paths the model cites verbatim."""
    unavailable: Dict[str, str] = field(default_factory=dict)
    """Source name -> why it could not contribute."""
    requested_mandi_id: Optional[str] = None
    """The id the caller asked for, when it differs from the canonical one.

    The cognition layer and the observation store key Bengaluru differently
    (`bangalore_apmc` vs `bangalore_yeshwanthpur`). Canonicalising for one
    breaks the other, so both spellings are kept and each source is tried
    against the one it actually uses."""

    def numeric_values(self) -> List[float]:
        """Every number the model is permitted to state.

        `grounding.py` checks the brief's figures against this list. Integers
        that are obviously not measurements (counts, horizons) are included
        too — excluding them would make a brief that correctly says "4
        horizons" look ungrounded.
        """
        out: List[float] = []
        for value in self.facts.values():
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                out.append(float(value))
        return out

    def render(self) -> str:
        """The evidence block as the model sees it."""
        lines = [
            f"COMMODITY: {self.commodity}",
            f"MANDI: {self.mandi_id}",
            f"EVIDENCE ASSEMBLED AT: {self.assembled_at}",
            "",
            "FACTS (cite these keys verbatim in evidence_ref):",
        ]
        if self.facts:
            width = max(len(k) for k in self.facts)
            for key in sorted(self.facts):
                lines.append(f"  {key.ljust(width)} = {self.facts[key]}")
        else:
            lines.append("  (none)")

        lines.append("")
        lines.append("UNAVAILABLE SOURCES:")
        if self.unavailable:
            for source in sorted(self.unavailable):
                lines.append(f"  {source}: {self.unavailable[source]}")
        else:
            lines.append("  (none — every source contributed)")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "commodity": self.commodity,
            "mandi_id": self.mandi_id,
            "assembled_at": self.assembled_at,
            "facts": self.facts,
            "unavailable": self.unavailable,
        }


def spoilage_adjusted_change_pct(commodity: str, horizon: Any, change_pct: Any) -> Optional[float]:
    """Expected change after shelf-life loss, from the farmer tools' own profiles.

    A direction call is not an economic instruction: holding a crop that loses
    8% a day for five days needs a price rise of ~50% just to break even. The
    same compounding rule `farmer/storage.py` applies is used here so the two
    surfaces cannot disagree. Past the shelf life the crop is unsellable, so
    the outlook is reported as a total loss.
    """
    if change_pct is None or not horizon:
        return None
    try:
        from mandisense_ai.farmer.reference import shelf_profile

        profile = shelf_profile(commodity)
    except Exception:  # pragma: no cover - reference module is always importable
        return None
    if int(horizon) > profile.shelf_life_days:
        return -100.0
    surviving = (1 - profile.daily_loss_pct / 100.0) ** int(horizon)
    return round(((1 + float(change_pct) / 100.0) * surviving - 1) * 100.0, 2)


def _add_forecast(bundle: EvidenceBundle) -> None:
    """Phase 2 scheduled forecast: horizons, intervals, measured skill."""
    try:
        from mandisense_ai.forecasting.service import get_forecast_service

        service = get_forecast_service()
        if not service.is_available:
            bundle.unavailable["forecast"] = "no published forecast store"
            return

        curve = service.get_curve(bundle.commodity, bundle.mandi_id)
        if not curve:
            bundle.unavailable["forecast"] = (
                f"{bundle.commodity} @ {bundle.mandi_id} is not a tracked series"
            )
            return

        for row in curve:
            status = row.get("status")
            horizon = row.get("horizon_days")
            if status != "OK":
                key = f"forecast.h{horizon}" if horizon else "forecast"
                bundle.facts[f"{key}.status"] = status
                if row.get("reason"):
                    bundle.facts[f"{key}.reason"] = row["reason"]
                continue

            key = f"forecast.h{horizon}"
            bundle.facts[f"{key}.point"] = row.get("forecast_price")
            bundle.facts[f"{key}.change_pct"] = row.get("expected_change_pct")
            bundle.facts[f"{key}.net_change_after_spoilage_pct"] = spoilage_adjusted_change_pct(
                bundle.commodity, horizon, row.get("expected_change_pct")
            )
            bundle.facts[f"{key}.direction"] = row.get("direction")
            interval = row.get("interval") or {}
            bundle.facts[f"{key}.p05"] = interval.get("p05")
            bundle.facts[f"{key}.p95"] = interval.get("p95")
            bundle.facts[f"{key}.model_skill"] = row.get("model_skill")

            # The validated recommendation and the calibrated probability it
            # was thresholded against. Without these the brief could only
            # cite `cognition.decision` — the legacy engine's call, which
            # disagrees on direction with this same forecast for three of the
            # ten tracked series — so the model was being handed the less
            # trustworthy of two answers and no way to tell them apart.
            if row.get("decision"):
                bundle.facts[f"{key}.decision"] = row.get("decision")
            if row.get("decision_probability_of_decline") is not None:
                bundle.facts[f"{key}.probability_of_decline"] = row.get(
                    "decision_probability_of_decline"
                )
            if row.get("interval_source"):
                bundle.facts[f"{key}.interval_source"] = row.get("interval_source")

        first = curve[0]
        bundle.facts["forecast.last_observed_price"] = first.get("last_observed_price")
        bundle.facts["forecast.as_of_date"] = first.get("as_of_date")
        bundle.facts["forecast.history_rows"] = first.get("history_rows")
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Evidence: forecast source failed: %s", exc)
        bundle.unavailable["forecast"] = f"error: {exc}"


def _add_spillover(bundle: EvidenceBundle) -> None:
    """Phase 2 spillover: transmission evidence, or why there is none."""
    try:
        from mandisense_ai.spillover.service import SpilloverService

        service = SpilloverService()
        status = service.status()
        if not status.get("available"):
            bundle.unavailable["spillover"] = "no spillover artifact built"
            return

        bundle.facts["spillover.total_edges"] = status.get("total_edges")
        bundle.facts["spillover.actionable_edges"] = status.get("actionable_edges")
        bundle.facts["spillover.placebo_verdict"] = status.get("placebo_verdict")
        bundle.facts["spillover.is_validated"] = status.get("is_validated")

        if not status.get("is_validated"):
            # The placebo gate withheld every edge. Saying so explicitly stops
            # the model reading an empty impact list as "no spillover risk".
            bundle.facts["spillover.interpretation"] = (
                "The permutation placebo failed, so every estimated edge is "
                "withheld. This means transmission could not be measured on "
                "the present panel — it does not mean transmission is absent."
            )
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Evidence: spillover source failed: %s", exc)
        bundle.unavailable["spillover"] = f"error: {exc}"


def _add_cognition(bundle: EvidenceBundle) -> None:
    """Phase 1 multi-agent cognition: the directive and its confidence."""
    try:
        from mandisense_ai.cognition.state_store import MarketMemoryStore

        store = MarketMemoryStore()
        # The cognition registry predates the canonical store ids, so try the
        # id the caller used before the canonical one rather than assuming
        # either layer's spelling is the authoritative one.
        candidates = [bundle.requested_mandi_id, bundle.mandi_id]
        state = None
        for candidate in [c for c in candidates if c]:
            state = store.get_latest_state(bundle.commodity, candidate)
            if state:
                break
        if not state:
            bundle.unavailable["cognition"] = "no cognition snapshot for this series"
            return

        # MarketState is a pydantic model; normalise to a plain dict so this
        # module does not depend on the cognition layer's model class.
        if hasattr(state, "model_dump"):
            data = state.model_dump()
        elif hasattr(state, "dict"):
            data = state.dict()
        else:
            data = dict(state)

        confidence = data.get("confidence") or {}
        bundle.facts["cognition.confidence_score"] = (
            confidence.get("score") if isinstance(confidence, dict) else confidence
        )
        bundle.facts["cognition.price_prediction"] = data.get("price_prediction")
        bundle.facts["cognition.trend"] = data.get("trend")
        bundle.facts["cognition.risk_level"] = data.get("risk_level")
        if data.get("regime"):
            bundle.facts["cognition.regime"] = str(data["regime"])

        # `directives` is a list ordered by priority; the first is the one the
        # product surfaces, so that is the one the brief may cite.
        directives = data.get("directives") or []
        if directives and isinstance(directives[0], dict):
            primary = directives[0]
            bundle.facts["cognition.decision"] = primary.get("action_code")
            bundle.facts["cognition.urgency"] = primary.get("urgency")
            if primary.get("reasoning"):
                bundle.facts["cognition.reasoning"] = primary["reasoning"]

        # Volatility regime — the feedback signal the ensemble re-weights on.
        volatility = data.get("volatility") or {}
        if isinstance(volatility, dict):
            bundle.facts["volatility.regime"] = volatility.get("regime")
            bundle.facts["volatility.score"] = volatility.get("score")
            bundle.facts["volatility.is_escalating"] = volatility.get("is_escalating")
            bundle.facts["volatility.momentum"] = volatility.get("momentum")
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Evidence: cognition source failed: %s", exc)
        bundle.unavailable["cognition"] = f"error: {exc}"


def _add_market(bundle: EvidenceBundle) -> None:
    """Observed price history — the ground truth the models are fit to."""
    try:
        from mandisense_ai.services import candle_data_service

        summary = candle_data_service.get_summary(bundle.commodity, bundle.mandi_id)
        if not summary:
            bundle.unavailable["market"] = "no observed history for this series"
            return
        for key in (
            "current_price",
            "week_change_pct",
            "month_change_pct",
            "year_change_pct",
            "as_of",
        ):
            if key in summary:
                bundle.facts[f"market.{key}"] = summary[key]
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Evidence: market source failed: %s", exc)
        bundle.unavailable["market"] = f"error: {exc}"


def build_evidence(commodity: str, mandi_id: str) -> EvidenceBundle:
    """Assemble the full evidence bundle for one series.

    Each source is independent: one failing leaves the others intact and is
    recorded under `unavailable`, because a brief that says "the forecast was
    unavailable" is honest, while one that quietly omits it is not.
    """
    # Resolve through the same canonical mapping the forecasting store and
    # the ingestion path use. Phase 1 surfaces address Bengaluru as
    # `bangalore_apmc` while the observation store keys it as
    # `bangalore_yeshwanthpur`; without this the sources below would each
    # resolve a different market and the bundle would mix two series.
    try:
        from mandisense_ai.forecasting.naming import (
            canonical_commodity,
            canonical_market,
        )

        resolved_commodity = canonical_commodity(commodity) or commodity.strip().lower()
        resolved_mandi = canonical_market(mandi_id) or mandi_id.strip().lower()
    except Exception:  # pragma: no cover - naming is always importable here
        resolved_commodity = commodity.strip().lower()
        resolved_mandi = mandi_id.strip().lower()

    bundle = EvidenceBundle(
        commodity=resolved_commodity,
        mandi_id=resolved_mandi,
        assembled_at=datetime.now(timezone.utc).isoformat(),
    )
    bundle.requested_mandi_id = mandi_id.strip().lower()
    _add_market(bundle)
    _add_cognition(bundle)
    _add_forecast(bundle)
    _add_spillover(bundle)

    # Drop keys whose value is None so the model is never shown "= None" and
    # invited to treat it as a measurement.
    bundle.facts = {k: v for k, v in bundle.facts.items() if v is not None}
    return bundle
