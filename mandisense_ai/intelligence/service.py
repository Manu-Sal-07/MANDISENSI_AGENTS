"""
Decision intelligence service.

Orchestrates one brief: assemble evidence, ask a provider to reason over it,
verify the answer against the evidence, attach provenance, return.

The service never raises into a request. A provider that fails falls back to
the deterministic one; a brief that fails grounding is still returned, marked
`grounded: false` with its issues listed. Both are honest outcomes. A 500
would tell the operator nothing and lose the evidence that was already
gathered.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from mandisense_ai.intelligence.evidence import EvidenceBundle, build_evidence
from mandisense_ai.intelligence.grounding import verify_grounding
from mandisense_ai.intelligence.providers import (
    BriefProvider,
    DeterministicProvider,
    select_provider,
)
from mandisense_ai.intelligence.schema import DecisionBrief, brief_from_dict
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)


class DecisionIntelligenceService:
    def __init__(self, provider: Optional[BriefProvider] = None):
        self._provider = provider or select_provider()

    @property
    def provider_name(self) -> str:
        return self._provider.name

    def status(self) -> Dict[str, Any]:
        return {
            "available": True,
            "provider": self._provider.name,
            "model_id": self._provider.model_id,
            "grounding_enforced": True,
        }

    def build_brief(
        self,
        commodity: str,
        mandi_id: str,
        evidence: Optional[EvidenceBundle] = None,
    ) -> DecisionBrief:
        started = time.time()
        bundle = evidence or build_evidence(commodity, mandi_id)

        provider = self._provider
        fell_back = False
        try:
            payload = provider.generate(bundle)
        except Exception as exc:
            # Losing the reasoning layer should degrade the brief, not the
            # request. The deterministic provider reads the same evidence.
            logger.warning(
                "Provider '%s' failed (%s); falling back to deterministic",
                provider.name,
                exc,
            )
            provider = DeterministicProvider()
            fell_back = True
            payload = provider.generate(bundle)

        brief = brief_from_dict(payload)

        # The model does not get to name its own series; that comes from the
        # request, so a brief can never be attributed to the wrong market.
        brief.commodity = bundle.commodity
        brief.mandi_id = bundle.mandi_id

        grounded, issues = verify_grounding(
            brief,
            allowed_numbers=bundle.numeric_values(),
            allowed_keys=list(bundle.facts.keys()),
        )
        brief.grounded = grounded
        brief.grounding_issues = issues

        brief.generated_by = provider.name + (" (fallback)" if fell_back else "")
        brief.model_id = provider.model_id
        brief.evidence_as_of = bundle.facts.get("forecast.as_of_date") or bundle.facts.get(
            "market.as_of"
        )

        if not grounded:
            logger.warning(
                "Brief for %s@%s failed grounding: %s",
                bundle.commodity,
                bundle.mandi_id,
                "; ".join(issues),
            )

        logger.info(
            "Brief for %s@%s via %s in %.0fms (grounded=%s)",
            bundle.commodity,
            bundle.mandi_id,
            brief.generated_by,
            (time.time() - started) * 1000,
            grounded,
        )
        return brief


_service: Optional[DecisionIntelligenceService] = None


def get_intelligence_service() -> DecisionIntelligenceService:
    global _service
    if _service is None:
        _service = DecisionIntelligenceService()
    return _service
