"""
Brief providers.

Two implementations behind one interface:

* `ClaudeProvider` calls the Claude API and has the model fill the brief
  schema through a tool call, so the result arrives as a validated dict
  rather than JSON parsed out of prose.

* `DeterministicProvider` composes the same structure from the evidence with
  explicit rules and no network.

The deterministic provider is the **default**, and that is a design decision
rather than a placeholder. A procurement recommendation should not silently
change because a network call was slow, nor should a live demo depend on a
third party being up. The Claude provider is enabled explicitly by setting
`ANTHROPIC_API_KEY`, and the brief always records which one produced it.

Both return the same shape, so `grounding.py` checks both identically — the
deterministic provider is not exempt from verification just because it is
incapable of hallucinating.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from mandisense_ai.intelligence.evidence import EvidenceBundle
from mandisense_ai.intelligence.schema import BRIEF_TOOL_SCHEMA
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_MODEL = "claude-opus-5"

SYSTEM_PROMPT = """\
You are a procurement analyst for Indian agricultural commodity markets \
(mandis). You write one decision brief for one commodity at one mandi.

You will be given an EVIDENCE block. It is the only thing you know.

Rules, in order of importance:

1. Never state a number that is not in the EVIDENCE block. Do not compute, \
derive, convert, average or estimate figures. If you want to express a \
magnitude you do not have, describe it in words instead.
2. Every factor must cite an evidence key in `evidence_ref`, spelled exactly \
as it appears in the EVIDENCE block.
3. If the evidence does not support a recommendation, set confidence to \
INSUFFICIENT_EVIDENCE and say plainly what is missing. This is a correct \
answer and is preferred over a confident guess.
4. Treat a forecast interval as the decision-relevant output, not the point \
estimate. Measured skill over a naive "price unchanged" baseline is only a \
few percent, so never describe a point forecast as what the price will be.
5. A withheld spillover result means transmission could not be measured. It \
does not mean there is no transmission. Never report it as safety.
6. Sources listed as UNAVAILABLE are unknown, not zero and not benign.

Call `publish_decision_brief` exactly once. Write for an operator deciding \
whether to buy today: direct, specific, no hedging filler."""


class BriefProvider(ABC):
    """Produces the raw brief payload for an evidence bundle."""

    name: str = "abstract"

    @abstractmethod
    def generate(self, evidence: EvidenceBundle) -> Dict[str, Any]:
        """Return a dict matching the brief tool schema."""

    @property
    def model_id(self) -> Optional[str]:
        return None


class ClaudeProvider(BriefProvider):
    """Claude, constrained to the brief schema through a tool call."""

    name = "claude"

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        import anthropic

        self._model = model or os.getenv("MANDISENSE_LLM_MODEL", DEFAULT_MODEL)
        # A zero-arg client also resolves an `ant auth login` profile, so an
        # unset ANTHROPIC_API_KEY does not necessarily mean no credentials.
        self._client = (
            anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        )

    @property
    def model_id(self) -> Optional[str]:
        return self._model

    def generate(self, evidence: EvidenceBundle) -> Dict[str, Any]:
        import anthropic

        try:
            response = self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                thinking={"type": "adaptive"},
                tools=[BRIEF_TOOL_SCHEMA],
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "EVIDENCE\n"
                            "========\n"
                            f"{evidence.render()}\n\n"
                            "Publish the decision brief."
                        ),
                    }
                ],
            )
        except anthropic.APIStatusError as exc:
            raise RuntimeError(f"Claude API error {exc.status_code}: {exc.message}") from exc
        except anthropic.APIConnectionError as exc:
            raise RuntimeError(f"Claude API unreachable: {exc}") from exc

        # A safety decline is a real outcome, not an exception; check it
        # before reading content.
        if response.stop_reason == "refusal":
            raise RuntimeError("Claude declined to produce a brief for this input")

        for block in response.content:
            if block.type == "tool_use" and block.name == BRIEF_TOOL_SCHEMA["name"]:
                # Tool inputs arrive parsed; never string-match the raw JSON.
                return dict(block.input)

        raise RuntimeError(
            f"Claude returned no brief tool call (stop_reason={response.stop_reason})"
        )


class DeterministicProvider(BriefProvider):
    """Composes a brief from the evidence with explicit rules.

    Every sentence is assembled from values already in the bundle, so this
    provider cannot state an ungrounded figure by construction. It is the
    default, and the fallback whenever the Claude provider cannot run.
    """

    name = "deterministic"

    def generate(self, evidence: EvidenceBundle) -> Dict[str, Any]:
        facts = evidence.facts
        factors: List[Dict[str, str]] = []
        risks: List[str] = []
        watch: List[str] = []

        commodity = evidence.commodity
        mandi = evidence.mandi_id.replace("_apmc", "").replace("_", " ")

        # --- forecast ------------------------------------------------
        horizon_key = next(
            (f"forecast.h{h}" for h in (5, 3, 7, 1) if f"forecast.h{h}.point" in facts),
            None,
        )
        change = facts.get(f"{horizon_key}.change_pct") if horizon_key else None
        direction = facts.get(f"{horizon_key}.direction") if horizon_key else None

        if horizon_key and change is not None:
            horizon_days = horizon_key.rsplit("h", 1)[-1]
            factors.append(
                {
                    "label": f"{horizon_days}-day scheduled forecast",
                    "detail": (
                        f"The published forecast moves {direction} by "
                        f"{change}% from the last observed close of "
                        f"{facts.get('forecast.last_observed_price')}, with a "
                        f"90% interval of {facts.get(f'{horizon_key}.p05')} to "
                        f"{facts.get(f'{horizon_key}.p95')}."
                    ),
                    # Direction is stated relative to buying sooner rather
                    # than later: a forecast rise is a reason to buy now, a
                    # forecast fall is a reason to wait.
                    "direction": "supports" if direction == "up" else "opposes",
                    "evidence_ref": f"{horizon_key}.change_pct",
                }
            )
            risks.append(
                "The interval is wide relative to the point estimate; measured "
                "skill over a naive unchanged-price baseline is only a few "
                "percent, so the band is the decision-relevant output."
            )
        else:
            refusal = next(
                (v for k, v in facts.items() if k.endswith(".status")), None
            )
            if refusal:
                risks.append(f"No forecast published for this series ({refusal}).")

        # --- cognition -----------------------------------------------
        cognition_decision = facts.get("cognition.decision")
        if cognition_decision:
            factors.append(
                {
                    "label": "Multi-agent cognition directive",
                    "detail": (
                        f"The agent ensemble currently reads {cognition_decision} "
                        f"with a confidence score of "
                        f"{facts.get('cognition.confidence_score')}."
                    ),
                    "direction": "supports",
                    "evidence_ref": "cognition.decision",
                }
            )

        # --- market --------------------------------------------------
        if "market.month_change_pct" in facts:
            month = facts["market.month_change_pct"]
            factors.append(
                {
                    "label": "Observed trend",
                    "detail": (
                        f"Realised price has moved {month}% over the past month, "
                        f"against a current level of "
                        f"{facts.get('market.current_price')}."
                    ),
                    # A falling realised trend argues against buying now.
                    "direction": "opposes" if month < 0 else "supports",
                    "evidence_ref": "market.month_change_pct",
                }
            )

        # --- spillover -----------------------------------------------
        if facts.get("spillover.is_validated") is False:
            factors.append(
                {
                    "label": "Cross-commodity spillover",
                    "detail": (
                        "The spillover engine estimated "
                        f"{facts.get('spillover.total_edges')} edges and its "
                        "permutation placebo failed, so every edge is withheld. "
                        "Transmission could not be measured — this is not "
                        "evidence that transmission is absent."
                    ),
                    "direction": "neutral",
                    "evidence_ref": "spillover.placebo_verdict",
                }
            )
            watch.append(
                "Spillover becomes usable once several commodities are observed "
                "in the same market, which holds geography fixed."
            )

        for source, reason in evidence.unavailable.items():
            risks.append(f"{source} unavailable ({reason}) — treated as unknown.")

        # --- action ---------------------------------------------------
        # The calibrated policy (forecasting/decision.py) is the only decision
        # rule whose precision has been measured out of sample, so when the
        # forecast carries one it decides the action; the +-2% rule below is
        # only the fallback for series that publish a forecast without it.
        policy = facts.get(f"{horizon_key}.decision") if horizon_key else None
        net = facts.get(f"{horizon_key}.net_change_after_spoilage_pct") if horizon_key else None

        if net is not None:
            factors.append(
                {
                    "label": "Spoilage-adjusted outlook",
                    "detail": (
                        f"After shelf-life loss the expected change is {net}%, "
                        "so a rise in price only pays if it outruns spoilage."
                    ),
                    "direction": "supports" if net > 0 else "opposes",
                    "evidence_ref": f"{horizon_key}.net_change_after_spoilage_pct",
                }
            )

        if change is None and not cognition_decision:
            action, confidence = "WAIT", "INSUFFICIENT_EVIDENCE"
            headline = (
                f"Insufficient evidence to advise on {commodity} at {mandi}."
            )
        elif policy == "HOLD" and net is not None and net <= 0:
            # Direction alone is not enough: the shipped hold-or-sell tool would
            # sell here, and the economic backtest shows ungated HOLD calls lose
            # money on fast-spoiling crops.
            action, confidence = "SELL", "MEDIUM"
            headline = (
                f"Holding {commodity} at {mandi} does not pay after spoilage; sell now."
            )
        elif policy in ("SELL", "HOLD"):
            action, confidence = policy, "MEDIUM"
            headline = (
                f"Validated policy reads {policy} for {commodity} at {mandi}."
            )
        elif policy == "WAIT":
            action, confidence = "WAIT", "LOW"
            headline = (
                f"Policy abstains for {commodity} at {mandi}; the band straddles zero."
            )
        elif change is not None and change <= -2:
            action, confidence = "WAIT", "MEDIUM"
            headline = f"Forecast points lower for {commodity} at {mandi}; hold off."
        elif change is not None and change >= 2:
            action, confidence = "BUY", "MEDIUM"
            headline = f"Forecast points higher for {commodity} at {mandi}; buy earlier."
        else:
            action, confidence = str(cognition_decision or "WAIT").upper(), "LOW"
            headline = f"No decisive move signalled for {commodity} at {mandi}."

        watch.append("Next scheduled forecast publish refreshes this brief.")

        rationale = (
            f"This brief rests on {len(factors)} evidence source(s). "
            f"Forecasts are published by a scheduled "
            "offline job rather than computed on request, so the as-of date "
            "shown is the date the evidence describes. Where a source could not "
            "contribute it is listed as a risk rather than omitted."
        )

        return {
            "commodity": commodity,
            "mandi_id": evidence.mandi_id,
            "action": action,
            "confidence": confidence,
            "headline": headline,
            "rationale": rationale,
            "factors": factors,
            "risks": risks,
            "watch_next": watch,
        }


def select_provider(prefer: Optional[str] = None) -> BriefProvider:
    """Pick a provider.

    Resolution order: an explicit `prefer` argument, then
    `MANDISENSE_LLM_PROVIDER`, then the deterministic default. Choosing
    Claude without usable credentials falls back rather than failing the
    request — the brief records which provider actually ran, so the
    degradation is reported rather than hidden.
    """
    choice = (prefer or os.getenv("MANDISENSE_LLM_PROVIDER") or "deterministic").lower()

    if choice in ("claude", "anthropic", "llm"):
        try:
            return ClaudeProvider()
        except Exception as exc:
            logger.warning(
                "Claude provider unavailable (%s); using deterministic provider", exc
            )
            return DeterministicProvider()

    return DeterministicProvider()
