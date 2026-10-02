"""
Phase 1 -> Phase 2 integration verification.

Answers one question with evidence rather than assertion: does every market
the Phase 1 product can display also resolve in the Phase 2 forecasting and
spillover engines?

It derives the universe from the running API rather than from a hardcoded
list, so it cannot silently pass by checking a smaller set than the product
actually offers.

A refusal (INSUFFICIENT_HISTORY, DORMANT, REBUILDING_HISTORY,
NO_PROMOTED_MODEL) counts as *resolved*: the series was found and the system
gave a reasoned answer. Only a 404 — the series being unreachable at all — is
an integration failure, because that is the one outcome that means the two
halves of the system address different markets.

Usage
-----
    python scripts/verify_phase2_integration.py
    python scripts/verify_phase2_integration.py --base-url http://localhost:8000

Exit codes: 0 if every Phase 1 pair resolves, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from collections import Counter
from typing import Any, Dict, Optional, Tuple

DEFAULT_BASE_URL = "http://localhost:8000"

# The API rate-limits; a verification run should not trip it and report its
# own throttling as a coverage failure.
REQUEST_SPACING_SECONDS = 0.35


def fetch(base_url: str, path: str, timeout: int = 30) -> Tuple[Any, Optional[Dict[str, Any]]]:
    """Return (status, body). Status is an int, or the string 'ERR'."""
    try:
        with urllib.request.urlopen(base_url + path, timeout=timeout) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read())
        except Exception:
            return exc.code, None
    except Exception as exc:
        return "ERR", {"error": str(exc)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    print("=" * 74)
    print("PHASE 1 -> PHASE 2 INTEGRATION VERIFICATION")
    print("=" * 74)

    # ── Health ────────────────────────────────────────────────────────
    status, health = fetch(base, "/v1/health")
    if health is None:
        print(f"\nCannot reach the API at {base} (status {status}).")
        print("Start it with: uvicorn api.main:app --host 0.0.0.0 --port 8000")
        return 1

    print(f"\nHealth: {health.get('status')}  ({health.get('probe_duration_ms')} ms)")
    for name, component in (health.get("components") or {}).items():
        phase = component.get("phase")
        phase_label = f"phase {phase}" if phase else "infra"
        state = component.get("status") or component.get("reachability")
        print(f"  {name:14} {phase_label:8} {state}")

    # ── The universe the Phase 1 product can display ──────────────────
    status, markets = fetch(base, "/v1/market-data/markets")
    if not markets:
        print("\nCould not read the Phase 1 market universe.")
        return 1

    pairs = [
        (commodity, mandi)
        for commodity in markets.get("commodities", [])
        for mandi in markets.get("markets", {}).get(commodity, [])
    ]

    print(f"\nPhase 1 displayable universe: {len(pairs)} commodity x mandi pairs")

    # ── Forecast coverage ─────────────────────────────────────────────
    print("\nQuerying the Phase 2 forecast endpoint for each pair...")
    outcomes: Counter = Counter()
    unreachable = []

    for commodity, mandi in pairs:
        time.sleep(REQUEST_SPACING_SECONDS)
        status, body = fetch(base, f"/v1/forecast/{commodity}/{mandi}?horizon=5")
        if status == 200 and body:
            points = body.get("points") or []
            outcomes[(points[0].get("status") if points else None) or "OK"] += 1
        else:
            outcomes[f"HTTP {status}"] += 1
            unreachable.append((commodity, mandi, status))

    print("\nOutcome for each Phase 1 pair:")
    for outcome, count in sorted(outcomes.items(), key=lambda item: -item[1]):
        print(f"  {str(outcome):28} {count}")

    resolved = len(pairs) - len(unreachable)
    published = outcomes.get("OK", 0)

    print()
    print(f"  Resolved (no 404)     {resolved}/{len(pairs)}")
    print(f"  Live forecast shown   {published}/{len(pairs)}")

    if unreachable:
        print("\nUnreachable pairs - these would 404 in the UI:")
        for commodity, mandi, status in unreachable[:20]:
            print(f"  {status}  {commodity:12} {mandi}")

    # ── Spillover ─────────────────────────────────────────────────────
    status, spillover = fetch(base, "/v1/spillover/status")
    if spillover:
        print(
            f"\nSpillover: {spillover.get('total_edges')} edges estimated, "
            f"{spillover.get('actionable_edges')} served "
            f"(placebo {spillover.get('placebo_verdict')})"
        )
        if not spillover.get("is_validated"):
            print("  Withheld by the placebo gate - absence of evidence, reported as such.")

    ok = not unreachable
    print()
    print("=" * 74)
    print("RESULT:", "PASS - every Phase 1 market resolves in Phase 2" if ok
          else f"FAIL - {len(unreachable)} Phase 1 markets unreachable")
    print("=" * 74)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
