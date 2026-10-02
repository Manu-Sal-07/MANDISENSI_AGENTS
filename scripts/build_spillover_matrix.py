"""
Build the cross-commodity spillover matrix artifact.

Usage:
    python scripts/build_spillover_matrix.py [--output PATH] [--no-holdout]
                                             [--min-episodes N] [--fdr Q]
                                             [--dry-run]

This is an offline job. Run it after the preprocessing pipeline regenerates the
processed datasets; the API picks up the new artifact on its next reload.

Exit codes:
    0  artifact built (or dry run completed)
    1  build failed - the previous artifact, if any, is left untouched
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mandisense_ai.config.settings import settings  # noqa: E402
from mandisense_ai.spillover.build import build_spillover_matrix  # noqa: E402
from mandisense_ai.spillover.config import DEFAULT_CONFIG  # noqa: E402
from mandisense_ai.spillover.matrix import default_artifact_path  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Artifact destination (default: <models_dir>/spillover/spillover_matrix.json)",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=None,
        help="Directory of processed parquet datasets",
    )
    parser.add_argument(
        "--min-episodes",
        type=int,
        default=None,
        help="Evidence floor; edges below this are published as INSUFFICIENT_EVIDENCE",
    )
    parser.add_argument(
        "--fdr",
        type=float,
        default=None,
        help="Target false discovery rate for the Benjamini-Hochberg correction",
    )
    parser.add_argument(
        "--no-holdout",
        action="store_true",
        help="Skip the out-of-sample diagnostic (faster)",
    )
    parser.add_argument(
        "--placebo",
        type=int,
        default=0,
        metavar="N",
        help=(
            "Run an N-permutation placebo and record the verdict in the artifact. "
            "Recommended: 100. A FAIL verdict makes every edge non-actionable."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and print the summary without writing the artifact",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    config = DEFAULT_CONFIG
    overrides = {}
    if args.min_episodes is not None:
        overrides["min_episodes"] = args.min_episodes
    if args.fdr is not None:
        overrides["fdr_level"] = args.fdr
    if overrides:
        config = replace(config, **overrides)

    processed_dir = args.processed_dir or Path(settings.paths.processed_data)
    output_path = args.output or default_artifact_path(Path(settings.paths.models_dir))

    try:
        matrix = build_spillover_matrix(
            processed_dir,
            config=config,
            run_holdout=not args.no_holdout,
        )
    except Exception as exc:
        print(f"ERROR: spillover build failed: {exc}", file=sys.stderr)
        print("Existing artifact (if any) left untouched.", file=sys.stderr)
        return 1

    if args.placebo > 0:
        from mandisense_ai.spillover.validate import run_placebo

        print(f"Running {args.placebo}-permutation placebo...", file=sys.stderr)
        try:
            matrix.diagnostics["placebo"] = run_placebo(
                processed_dir, config=config, n_permutations=args.placebo
            )
        except Exception as exc:
            print(f"WARNING: placebo could not run: {exc}", file=sys.stderr)

    summary = matrix.summary()
    print(json.dumps(summary, indent=2, default=str))

    if matrix.placebo_verdict == "FAIL":
        print(
            "\nPLACEBO FAILED: randomised shock dates produced as many "
            "significant edges as the real ones. No edge is published as "
            "actionable. This is a data-width problem, not a code problem - "
            "see the report in docs/.",
            file=sys.stderr,
        )

    print("\nActionable edges:")
    if not matrix.actionable_edges:
        print("  (none survived the evidence and FDR gates)")
    for edge in sorted(
        matrix.actionable_edges, key=lambda e: -abs(e.peak_elasticity or 0.0)
    ):
        peak = next(e for e in edge.effects if e.horizon == edge.peak_horizon)
        print(
            f"  {edge.source:14s} {edge.shock_type:8s} -> {edge.target:14s} "
            f"h={edge.peak_horizon}  {(edge.peak_elasticity or 0) * 100:+6.2f}%  "
            f"CI[{peak.ci_low * 100:+6.1f},{peak.ci_high * 100:+6.1f}]  "
            f"n={edge.n_episodes}"
        )

    if args.dry_run:
        print("\nDry run: artifact not written.")
        return 0

    matrix.save(output_path)
    print(f"\nArtifact written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
