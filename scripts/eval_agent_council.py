"""
Evaluate the agent council against the single served forecaster, and publish its per-agent forecasts.

    python scripts/eval_agent_council.py

Writes  mandisense_ai/models/council/evaluation.json   walk-forward results, weights and the promotion decision per horizon
        mandisense_ai/models/council/forecasts.json    every series' latest forecast, per agent and fused
        docs/AGENT_COUNCIL.md                          the same results as a readable report
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from mandisense_ai.forecasting import council  # noqa: E402


def pct(x: float) -> str:
    return f"{100 * x:+.1f}%"


def report(result: dict) -> str:
    agents = list(result["agents"])
    L = ["# Agent council: evaluation", "",
         f"Generated {result['generated_at'][:19]}Z in {result['seconds']} s. Agents: " + ", ".join(f"`{k}` ({v} features)" for k, v in result["agents"].items()) + ".", "",
         "Each agent is a gradient-boosted model that sees only its own family of evidence. The meta-ensemble weights them with non-negative least squares fitted "
         "inside each walk-forward fold, on the agents' out-of-sample predictions for the later quarter of that fold's training window, so a fold never chooses "
         "weights with its own test period. Everything is scored on the same rows, folds and target as the single served model. Skill is the reduction in mean "
         "absolute error against a forecast of no change.", "",
         f"Promotion rule: {result['rule']}.", "", "## Results", "",
         "| Horizon | n | No-change MAE | Single model | Equal-weight | Council (weights sum <= 1) | Council, unconstrained weights | Council vs single (MAE diff, 95% CI) | Folds won | Promoted |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for h, s in result["horizons"].items():
        m, c = s["methods"], s["council_vs_single"]
        L.append(f"| {h}d | {s['n']} | {s['no_change_mae']} | {pct(m['single']['skill'])} | {pct(m['equal']['skill'])} | {pct(m['council']['skill'])} | {pct(m['council_raw']['skill'])} | "
                 f"{c['mean_abs_error_diff']:+.5f} [{c['ci'][0]:+.5f}, {c['ci'][1]:+.5f}] | {s['folds_council_beats_single']}/{s['folds']} | {'yes' if s['promoted'] else 'no'} |")
    L += ["", "## Each agent alone (skill against no change)", "", "| Horizon | " + " | ".join(agents) + " |", "|---|" + "---|" * len(agents)]
    for h, s in result["horizons"].items():
        L.append(f"| {h}d | " + " | ".join(pct(s["methods"][a]["skill"]) for a in agents) + " |")
    L += ["", "## Learned weights (mean over folds)", "", "| Horizon | " + " | ".join(agents) + " | Sum | Sum before constraint |", "|---|" + "---|" * (len(agents) + 2)]
    for h, s in result["horizons"].items():
        L.append(f"| {h}d | " + " | ".join(f"{s['mean_weights'][a]:.2f}" for a in agents) + f" | {s['weight_sum']:.2f} | {s['unconstrained_weight_sum']:.2f} |")
    L += ["", "## When the feed carries no arrival volumes", "", "| Horizon | Single | Council |", "|---|---|---|"]
    for h, s in result["horizons"].items():
        L.append(f"| {h}d | {pct(s['arrival_masked_skill']['single'])} | {pct(s['arrival_masked_skill']['council'])} |")
    promoted = [h for h, s in result["horizons"].items() if s["promoted"]]
    L += ["", "## Reading", "",
          ("The council is promoted at " + ", ".join(f"{h}d" for h in promoted) + ": its improvement over the single model is significant and consistent across folds."
           if promoted else
           "The council is **not** promoted at any horizon: its difference from the single model is not significant, or it does not win enough folds. "
           "It is kept as an explanation of what each specialist sees, and the served forecast remains the single model."), "",
          "External factors (weather, news) are shown as live context and carry no forecast weight, because there is no historical panel of them to validate a weight against.", "",
          "## Limits", "",
          "- All agents share one learner family and one panel, so their errors are correlated and a weighted average can add little.",
          "- Skills at these horizons are small in absolute terms; differences of a fraction of a percentage point need the intervals above to be read, not the point values.",
          "- The weights are fitted on a quarter of each training window, which is a deliberately small sample.",
          "- The unconstrained version was the first design and is kept in the table: it was worse because least squares inflated weak agent forecasts (weights summing to 2-3); constraining the sum was a change made after seeing that result, not before."]
    return "\n".join(L)


def main() -> None:
    result = council.run()
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "AGENT_COUNCIL.md").write_text(report(result), encoding="utf-8")
    for h, s in result["horizons"].items():
        print(f"h={h}d  single {pct(s['methods']['single']['skill'])}  council {pct(s['methods']['council']['skill'])}  "
              f"diff {s['council_vs_single']['mean_abs_error_diff']:+.5f} CI {s['council_vs_single']['ci']}  "
              f"folds {s['folds_council_beats_single']}/{s['folds']}  promoted={s['promoted']}")
    print("wrote docs/AGENT_COUNCIL.md")


if __name__ == "__main__":
    main()
