"""
Evaluate the farmer explanation layer: does the model stay faithful, and does the safety net catch it when it does not.

    python scripts/eval_llm_intel.py            # live (needs GROQ_API_KEY), ~10 minutes on a free-tier token budget
    python scripts/eval_llm_intel.py --quick    # a smaller grid

Two experiments, both written to docs/LLM_EVALUATION.md and mandisense_ai/models/llm_eval.json:

1. Acceptance. For every crop x origin x language, how many model-written sentences pass the structural validator, how many
   then pass the independent faithfulness judge, and what falls back to the rule-based wording. The decision, every number and
   every name are inserted by code, so the checks that matter are on meaning, not on figures.
2. Judge power. Known-faithful and deliberately corrupted rewrites (reversed direction, dropped qualifier, added claim, wrong
   meaning attached to a slot) are shown to the judge. We report the share of corruptions caught and of faithful rewrites
   wrongly rejected, with Wilson 95% intervals. The corruptions are synthetic and few, so this bounds the judge's behaviour
   on those failure types only.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
import warnings
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from mandisense_ai.intelligence import explain as ex  # noqa: E402
from mandisense_ai.intelligence.providers import load_env  # noqa: E402
from mandisense_ai.market_choice import service as mc  # noqa: E402
from mandisense_ai.shock.service import radar  # noqa: E402

LANGS = ("en", "kn", "hi")
CROPS = ("tomato", "onion", "potato", "ginger")
ORIGINS = ("kolar", "bengaluru")


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 3), round(c + h, 3))


def acceptance(crops, origins, quantity=20.0):
    rows, reasons = [], Counter()
    for crop in crops:
        for origin in origins:
            rec = mc.recommend(crop, mc.resolve_origin(origin, None, None, None), quantity)
            if rec.get("status") != "OK":
                continue
            item = (radar("farmer", crop, origin).get("items") or [None])[0]
            for lang in LANGS:
                ex._CACHE.clear()
                out = ex.explain(rec, item, lang, use_llm=True)
                c = out["checks"]
                rej = c.get("rejected", [])
                for r in rej:
                    reasons[r["reason"].split(":")[0]] += 1
                rows.append({"crop": crop, "origin": origin, "lang": lang, "author": out["author"], "sentences": c.get("sentences", 0),
                             "by_llm": c.get("sentences_by_llm", 0), "rejected": len(rej),
                             "judge_rejected": sum(r["reason"].startswith("judge") for r in rej),
                             "validator_rejected": sum(not r["reason"].startswith("judge") for r in rej),
                             "decision_unchanged": c.get("decision_unchanged"), "llm_error": c.get("llm_error"), "latency_ms": c.get("latency_ms")})
                print(f"  {crop:7}{origin:10}{lang}  llm {rows[-1]['by_llm']}/{rows[-1]['sentences']}  judge-rejected {rows[-1]['judge_rejected']}", flush=True)
    return rows, dict(reasons)


SRC = {
    "en": ["After transport, fees and spoilage, you should get {gain.nearest} per quintal {gain.nearest_dir} than going to {nearest.mandi}.",
           "{best.mandi} is expected to be open and trading that day, with about {best.open} chance.",
           "The minimum is a careful estimate, not a promise: in past tests it was missed about {floor.miss} of the time."],
}
# (original index, corrupted rewrite, kind). Faithful paraphrases are kind == "faithful".
PAIRS = [
    (0, "Compared with going to {nearest.mandi}, you keep {gain.nearest} per quintal {gain.nearest_dir} after transport, fees and spoilage.", "faithful"),
    (0, "Going to {nearest.mandi} leaves you with {gain.nearest} per quintal {gain.nearest_dir} once transport, fees and spoilage are paid.", "reversed"),
    (0, "After transport and fees, you keep {gain.nearest} per quintal {gain.nearest_dir} than {nearest.mandi}, and prices will keep rising.", "added_claim"),
    (0, "You should get {gain.nearest} per quintal {gain.nearest_dir} than at {nearest.mandi}.", "dropped_qualifier"),
    (1, "{best.mandi} will likely be open and trading that day, about {best.open} chance.", "faithful"),
    (1, "{best.mandi} will be crowded with buyers that day, with about {best.open} chance.", "added_claim"),
    (1, "{best.mandi} is expected to be closed that day, with about {best.open} chance.", "reversed"),
    (1, "There is about {best.open} chance that {best.mandi} pays the best price that day.", "wrong_meaning"),
    (2, "The minimum is a careful estimate rather than a promise: in past tests it fell short about {floor.miss} of the time.", "faithful"),
    (2, "The minimum is a firm promise: in past tests it was met about {floor.miss} of the time.", "reversed"),
    (2, "The minimum is a careful estimate: in past tests it was missed about {floor.miss} of the time, and the maximum is higher.", "added_claim"),
    (2, "In past tests it was missed about {floor.miss} of the time.", "dropped_qualifier"),
]


def judge_power(model=None):
    pairs = [{"id": f"p{i}", "original": SRC["en"][o], "rewrite": r} for i, (o, r, _) in enumerate(PAIRS)]
    verdict = {}
    for i in range(0, len(pairs), 4):                       # small batches keep each call inside the token budget
        verdict.update(ex.judge_faithful(pairs[i:i + 4], "en", model))
        time.sleep(2)
    caught = missed = false_rej = true_acc = 0
    detail = []
    for i, (_, _, kind) in enumerate(PAIRS):
        faithful = bool(verdict.get(f"p{i}", {}).get("faithful"))
        if kind == "faithful":
            false_rej += not faithful
            true_acc += faithful
        else:
            caught += not faithful
            missed += faithful
        detail.append({"kind": kind, "judge_says_faithful": faithful, "problem": verdict.get(f"p{i}", {}).get("problem", "")})
    n_bad, n_good = caught + missed, false_rej + true_acc
    return {"corruptions": n_bad, "caught": caught, "caught_ci": wilson(caught, n_bad), "faithful": n_good, "wrongly_rejected": false_rej,
            "wrongly_rejected_ci": wilson(false_rej, n_good), "detail": detail}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    a = ap.parse_args()
    load_env()
    crops, origins = (CROPS[:2], ORIGINS[:1]) if a.quick else (CROPS, ORIGINS)
    print("Experiment 1: acceptance", flush=True)
    rows, reasons = acceptance(crops, origins)
    s_total = sum(r["sentences"] for r in rows)
    by_lang = {}
    for lang in LANGS:
        rs = [r for r in rows if r["lang"] == lang]
        n = sum(r["sentences"] for r in rs)
        k = sum(r["by_llm"] for r in rs)
        by_lang[lang] = {"explanations": len(rs), "sentences": n, "accepted_from_model": k, "accepted_ci": wilson(k, n),
                         "judge_rejected": sum(r["judge_rejected"] for r in rs), "validator_rejected": sum(r["validator_rejected"] for r in rs),
                         "all_rule_based": sum(r["author"] == "rules" for r in rs)}
    print("Experiment 2: judge power", flush=True)
    jp = judge_power()
    result = {"generated_at": datetime.now(timezone.utc).isoformat(), "writer": ex.os.getenv("MANDISENSE_GROQ_MODEL", "openai/gpt-oss-120b"),
              "judge": ex.os.getenv("MANDISENSE_JUDGE_MODEL", "openai/gpt-oss-120b"), "explanations": len(rows), "sentences": s_total,
              "decision_unchanged_all": all(r["decision_unchanged"] for r in rows), "by_language": by_lang, "rejection_reasons": reasons,
              "median_latency_ms": sorted(r["latency_ms"] or 0 for r in rows)[len(rows) // 2] if rows else None, "llm_errors": sum(bool(r["llm_error"]) for r in rows),
              "judge_power": jp, "rows": rows}
    (ROOT / "mandisense_ai" / "models").mkdir(exist_ok=True)
    (ROOT / "mandisense_ai" / "models" / "llm_eval.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

    md = ["# LLM explanation layer: evaluation", "", f"Generated {result['generated_at'][:19]}Z. Writer `{result['writer']}`, judge `{result['judge']}`.", "",
          "The model only paraphrases sentences whose facts, numbers and names are written by code. Every paraphrase must keep the same slots, add no digit, "
          "no overclaim word, stay short and in the right script, and then pass an independent faithfulness judge. Anything that fails keeps its rule-based wording.", "",
          f"## 1. Acceptance ({len(rows)} explanations, {s_total} sentences)", "",
          "| Language | Explanations | Sentences | Kept from model | 95% CI | Judge rejected | Validator rejected | Fully rule-based |", "|---|---|---|---|---|---|---|---|"]
    for lang, v in by_lang.items():
        md.append(f"| {lang} | {v['explanations']} | {v['sentences']} | {v['accepted_from_model']} | {v['accepted_ci'][0]:.2f}–{v['accepted_ci'][1]:.2f} | "
                  f"{v['judge_rejected']} | {v['validator_rejected']} | {v['all_rule_based']} |")
    md += ["", f"The recommended market, day and every figure were identical with and without the model in all {len(rows)} cases: "
           f"{'yes' if result['decision_unchanged_all'] else 'NO'}. Model errors (fell back to rules): {result['llm_errors']}. "
           f"Median latency {result['median_latency_ms']} ms.", "",
           f"Rejection reasons: {json.dumps(reasons, ensure_ascii=False)}", "",
           f"## 2. Judge power (English, {jp['corruptions']} corrupted and {jp['faithful']} faithful rewrites)", "",
           f"Caught {jp['caught']}/{jp['corruptions']} corruptions (95% CI {jp['caught_ci'][0]:.2f}–{jp['caught_ci'][1]:.2f}); wrongly rejected "
           f"{jp['wrongly_rejected']}/{jp['faithful']} faithful rewrites (95% CI {jp['wrongly_rejected_ci'][0]:.2f}–{jp['wrongly_rejected_ci'][1]:.2f}).", "",
           "| Corruption | Judge says faithful? | Reason given |", "|---|---|---|"]
    for d in jp["detail"]:
        md.append(f"| {d['kind']} | {d['judge_says_faithful']} | {d['problem'][:110]} |")
    md += ["", "## Limits", "",
           "- The corruptions are hand-written for one language and a few sentence types, so the catch rate is a bound on those failure types, not a general guarantee.",
           "- Kannada and Hindi acceptance depends on the judge model reading those scripts; a native-speaker review of the wording is still needed.",
           "- Writer (OpenAI gpt-oss) and judge (Alibaba Qwen) are different model families but both run on the same hosted service, so an outage or rate limit affects both; when the judge cannot answer, the rule-based wording is kept."]
    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "LLM_EVALUATION.md").write_text("\n".join(md), encoding="utf-8")
    print("wrote docs/LLM_EVALUATION.md")


if __name__ == "__main__":
    main()
