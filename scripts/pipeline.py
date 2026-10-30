"""
One command from raw Agmarknet exports to every artifact the app serves.

    python scripts/pipeline.py                       # every stage, in order
    python scripts/pipeline.py --list                # show the stages and what each reads and writes
    python scripts/pipeline.py --only shock,council  # chosen stages
    python scripts/pipeline.py --skip research       # everything except chosen stages
    python scripts/pipeline.py --dry-run             # print the commands, run nothing
    python scripts/pipeline.py --with-research       # also re-run the full research experiments (hours)
    python scripts/pipeline.py --with-llm-eval       # also run the LLM evaluation (needs GROQ_API_KEY)

Stages run in dependency order and stop at the first failure (`--keep-going` continues). Each stage is an ordinary script that
can also be run by hand; this file only fixes the order, checks that a stage's inputs exist, times it and writes
`logs/pipeline_report.json`. Re-running is safe: every stage rewrites its own outputs from its inputs and nothing else.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable


@dataclass(frozen=True)
class Stage:
    name: str
    command: Sequence[str]
    reads: Sequence[str]
    writes: Sequence[str]
    purpose: str
    optional: Optional[str] = None            # flag that must be given to include this stage
    needs: Sequence[str] = field(default_factory=tuple)


STAGES: List[Stage] = [
    Stage("world", [PY, "scripts/build_farmer_world.py"],
          ["mandisense_ai/data/farmer/source/*.csv"],
          ["mandisense_ai/data/farmer/*.parquet", "mandisense_ai/models/farmer/"],
          "Ingest the Agmarknet exports into the district, mandi and market panels and train the district forecaster."),
    Stage("forecasts", [PY, "scripts/run_nightly_job.py", "--seed-history", "--no-ingest"],
          ["mandisense_ai/data/farmer/market_daily.parquet"],
          ["data/observations/market_observations.parquet", "mandisense_ai/models/forecast_models/", "mandisense_ai/models/forecasts/forecast_store.json"],
          "Seed the observation store from the market panel (idempotent upsert), retrain on cadence and publish the mandi-level forecast store the API serves.", needs=("world",)),
    Stage("market_choice", [PY, "scripts/build_market_choice.py"],
          ["mandisense_ai/data/farmer/market_daily.parquet"],
          ["mandisense_ai/models/market_choice/"],
          "Train the where-and-when-to-sell engine per crop, with its walk-forward backtest and conformal floor.", needs=("world",)),
    Stage("track_record", [PY, "scripts/build_track_record.py"],
          ["mandisense_ai/data/farmer/market_daily.parquet", "mandisense_ai/models/market_choice/"],
          ["mandisense_ai/models/market_choice/*/track_record.json"],
          "Replay the served advice day by day on out-of-sample days for the public track record; refuses to write if it disagrees with the engine's back-test.", needs=("market_choice",)),
    Stage("transmission", [PY, "scripts/build_transmission.py"],
          ["mandisense_ai/data/farmer/district_observations.parquet"],
          ["mandisense_ai/models/farmer/transmission_matrix.json"],
          "Test cross-commodity and cross-district transmission with placebo and multiplicity control.", needs=("world",)),
    Stage("shock", [PY, "scripts/build_shock_study.py"],
          ["mandisense_ai/data/farmer/district_observations.parquet", "mandisense_ai/models/farmer/transmission_matrix.json"],
          ["mandisense_ai/models/shock/shock_study.json"],
          "Event study of arrival gluts and squeezes: own-crop price response, with evidence tiers.", needs=("transmission",)),
    Stage("spillover", [PY, "scripts/build_spillover_matrix.py"],
          ["mandisense_ai/data/farmer/market_daily.parquet"],
          ["mandisense_ai/models/spillover/spillover_matrix.json"],
          "Weekly cross-commodity spillover matrix used as AI Brief evidence.", needs=("world",)),
    Stage("council", [PY, "scripts/eval_agent_council.py"],
          ["mandisense_ai/data/farmer/market_daily.parquet"],
          ["mandisense_ai/models/council/", "docs/AGENT_COUNCIL.md"],
          "Evaluate the specialist-agent council against the single served model and publish per-agent forecasts.", needs=("forecasts",)),
    Stage("research", [PY, "research/scripts/export_app_evidence.py"],
          ["research/results/"],
          ["mandisense_ai/data/market_choice/evidence.json", "frontend/public/evidence/"],
          "Export the paper's figures and numbers for the in-app Evidence page (re-runs nothing heavy)."),
    Stage("results", [PY, "scripts/build_results.py"],
          ["research/results/", "mandisense_ai/models/council/evaluation.json"],
          ["docs/RESULTS.md", "docs/figures/results/"],
          "Consolidate every experiment into one results document with figures, read from the artefacts.", needs=("council", "research")),
    Stage("research_full", [PY, "research/scripts/run_all_crops.py"],
          ["datasets/year_data/"], ["research/results/"],
          "Re-run the nested walk-forward experiments for every studied crop, and the leakage, foundation-model and silence audits (hours).", optional="with_research"),
    Stage("llm_eval", [PY, "scripts/eval_llm_intel.py"],
          ["mandisense_ai/models/market_choice/"], ["docs/LLM_EVALUATION.md", "mandisense_ai/models/llm_eval.json"],
          "Measure the LLM explanation layer's acceptance and the judge's power (needs GROQ_API_KEY).", optional="with_llm_eval"),
    Stage("tests", [PY, "-m", "pytest", "mandisense_ai", "-q", "-p", "no:cacheprovider"],
          [], [], "Run the application test suite."),
]


def _exists(pattern: str) -> bool:
    p = ROOT / pattern
    if "*" in pattern:
        return any(p.parent.glob(p.name))
    return p.exists()


def select(only: Optional[List[str]], skip: List[str], flags: Dict[str, bool]) -> List[Stage]:
    known = {s.name for s in STAGES}
    for n in (only or []) + skip:
        if n not in known:
            raise SystemExit(f"unknown stage '{n}'; choose from: {', '.join(sorted(known))}")
    chosen = [s for s in STAGES if (not only or s.name in only) and s.name not in skip]
    return [s for s in chosen if s.optional is None or flags.get(s.optional) or (only and s.name in only)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--only", type=lambda v: [x for x in v.split(",") if x])
    ap.add_argument("--skip", type=lambda v: [x for x in v.split(",") if x], default=[])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--keep-going", action="store_true")
    ap.add_argument("--with-research", action="store_true")
    ap.add_argument("--with-llm-eval", action="store_true")
    a = ap.parse_args()

    stages = select(a.only, a.skip, {"with_research": a.with_research, "with_llm_eval": a.with_llm_eval})
    if a.list:
        for s in STAGES:
            tag = f"  [needs --{s.optional.replace('_', '-')}]" if s.optional else ""
            print(f"{s.name:14s}{tag}\n    {s.purpose}\n    reads : {', '.join(s.reads) or '-'}\n    writes: {', '.join(s.writes) or '-'}")
        return 0

    report: Dict[str, object] = {"started": datetime.now(timezone.utc).isoformat(), "stages": []}
    failed = False
    for s in stages:
        cmd = list(s.command)
        print(f"\n=== {s.name}: {s.purpose}\n$ {' '.join(cmd)}", flush=True)
        missing = [r for r in s.reads if not _exists(r)]
        entry: Dict[str, object] = {"stage": s.name, "command": cmd}
        if missing:
            entry.update(status="SKIPPED_MISSING_INPUT", missing=missing)
            print(f"   skipped: missing input(s) {missing}; run the stage that writes them first")
            failed = failed or not a.keep_going
        elif a.dry_run:
            entry["status"] = "DRY_RUN"
        else:
            t0 = time.time()
            code = subprocess.run(cmd, cwd=ROOT).returncode
            entry.update(status="OK" if code == 0 else "FAILED", seconds=round(time.time() - t0, 1), exit_code=code)
            failed = failed or code != 0
            print(f"   {entry['status']} in {entry['seconds']} s")
        report["stages"].append(entry)  # type: ignore[union-attr]
        if failed and not a.keep_going:
            break

    report["finished"] = datetime.now(timezone.utc).isoformat()
    if not a.dry_run:
        out = ROOT / "logs"
        out.mkdir(exist_ok=True)
        (out / "pipeline_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print("\n" + "\n".join(f"{e['stage']:14s}{e['status']:24s}{e.get('seconds', '')}" for e in report["stages"]))  # type: ignore[union-attr]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
