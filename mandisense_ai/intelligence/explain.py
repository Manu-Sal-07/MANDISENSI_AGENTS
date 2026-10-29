"""
"Why this advice" for the farmer, in English, Kannada and Hindi.

The market-choice engine DECIDES where and when to sell and what minimum to
state. This module only EXPLAINS that decision, and it is built so that the
language model cannot change it:

  * the headline is composed by code from the recommendation (mandi, day, net,
    floor), so the model never touches the decision or any figure in it;
  * the reasons are first written by code as sentence templates, each already
    tied to the right facts (a "97%" is attached to "chance the mandi is open",
    never to anything else);
  * the model may only PARAPHRASE each sentence (fluency, tone, natural Kannada
    and Hindi). A paraphrase is accepted only if it keeps exactly the same
    `{placeholder}` slots as its source, adds no digit, adds no overclaim word
    ("guarantee", "certain", ...), stays short and is in the requested script;
    any sentence that fails keeps its rule-based wording. An earlier design that
    let the model choose placeholders freely produced correct numbers in wrong
    meanings (a neighbour price gap presented as profit), which no validator can
    detect, so assignment of meaning was taken away from the model;
  * every number, mandi name and date is inserted by code at the end, and the
    response says how many sentences each author wrote.

No call here changes a recommendation; the model is optional and every output is
checked.
"""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from mandisense_ai.intelligence.providers import load_env
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

LANGS = ("en", "kn", "hi")
MAX_WORDS = 34
OVERCLAIM = re.compile(r"\b(guarantee[sd]?|guaranteed|certain(ly)?|definitely|sure to|100\s*%|no risk|risk[- ]free|will surely)\b", re.I)
DIGITS = re.compile(r"[0-9०-९೦-೯]")
PLACEHOLDER = re.compile(r"\{([a-z_.]+)\}")
SCRIPT_RANGE = {"kn": (0x0C80, 0x0CFF), "hi": (0x0900, 0x097F)}

CROP_NAMES = {
    "tomato": {"en": "tomato", "kn": "ಟೊಮೆಟೊ", "hi": "टमाटर"}, "onion": {"en": "onion", "kn": "ಈರುಳ್ಳಿ", "hi": "प्याज"},
    "potato": {"en": "potato", "kn": "ಆಲೂಗಡ್ಡೆ", "hi": "आलू"}, "ginger": {"en": "ginger", "kn": "ಶುಂಠಿ", "hi": "अदरक"},
    "garlic": {"en": "garlic", "kn": "ಬೆಳ್ಳುಳ್ಳಿ", "hi": "लहसुन"},
}
MONTHS = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "kn": ["ಜನವರಿ", "ಫೆಬ್ರವರಿ", "ಮಾರ್ಚ್", "ಏಪ್ರಿಲ್", "ಮೇ", "ಜೂನ್", "ಜುಲೈ", "ಆಗಸ್ಟ್", "ಸೆಪ್ಟೆಂಬರ್", "ಅಕ್ಟೋಬರ್", "ನವೆಂಬರ್", "ಡಿಸೆಂಬರ್"],
    "hi": ["जन॰", "फ़र॰", "मार्च", "अप्रैल", "मई", "जून", "जुला॰", "अग॰", "सित॰", "अक्तू॰", "नव॰", "दिस॰"],
}
WEEKDAYS = {
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "kn": ["ಸೋಮವಾರ", "ಮಂಗಳವಾರ", "ಬುಧವಾರ", "ಗುರುವಾರ", "ಶುಕ್ರವಾರ", "ಶನಿವಾರ", "ಭಾನುವಾರ"],
    "hi": ["सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार"],
}
STATE_WORD = {
    "glut": {"en": "much higher than usual", "kn": "ಸಾಮಾನ್ಯಕ್ಕಿಂತ ತುಂಬಾ ಹೆಚ್ಚು", "hi": "सामान्य से बहुत ज़्यादा"},
    "elevated": {"en": "higher than usual", "kn": "ಸಾಮಾನ್ಯಕ್ಕಿಂತ ಹೆಚ್ಚು", "hi": "सामान्य से ज़्यादा"},
    "squeeze": {"en": "much lower than usual", "kn": "ಸಾಮಾನ್ಯಕ್ಕಿಂತ ತುಂಬಾ ಕಡಿಮೆ", "hi": "सामान्य से बहुत कम"},
    "low": {"en": "lower than usual", "kn": "ಸಾಮಾನ್ಯಕ್ಕಿಂತ ಕಡಿಮೆ", "hi": "सामान्य से कम"},
}


def rupees(v: float) -> str:
    return "₹" + format(int(round(v)), ",")


def _indian(v: float) -> str:
    s = str(int(round(abs(v))))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head)
        s = f"{head},{tail}"
    return "₹" + s


def build_facts(rec: Dict[str, Any], shock_item: Optional[Dict[str, Any]], lang: str) -> Dict[str, str]:
    """Render every placeholder value, in the reader's language, from the engine's own output."""
    best = rec["recommended"]
    is_gate = best["kind"] == "farm_gate"
    name_key = {"kn": "mandi_name_kn", "hi": "mandi_name_hi"}.get(lang, "mandi_name")
    wd = WEEKDAYS[lang][datetime.fromisoformat(best["sale_date"]).weekday()]
    d0 = datetime.fromisoformat(best["sale_date"])
    day = f"{d0.day} {MONTHS[lang][d0.month - 1]}"
    hold = best["hold_days"]
    when = {"en": ("today" if hold == 0 else f"in {hold} day{'s' if hold > 1 else ''}"),
            "kn": ("ಇಂದು" if hold == 0 else f"{hold} ದಿನದ ನಂತರ"), "hi": ("आज" if hold == 0 else f"{hold} दिन बाद")}[lang]
    facts = {
        "crop": CROP_NAMES.get(rec["crop"], {}).get(lang, rec["crop"]),
        "best.mandi": {"en": "your farm gate", "kn": "ನಿಮ್ಮ ಜಮೀನಿನಲ್ಲೇ", "hi": "अपने खेत पर"}[lang] if is_gate else best[name_key],
        "best.when": f"{when} ({wd}, {day})",
        "best.net": _indian(best["expected_net_per_q"]),
        "best.floor": _indian(best["floor_per_q"]),
        "best.open": f"{round(100 * best['chance_open'])}%",
        "best.distance": f"{best['distance_km']} km" if not is_gate else "0 km",
        "floor.confidence": f"{rec['confidence_pct']}%",
    }
    v = (rec.get("guarantee") or {}).get("backtest_violation")
    if v is not None:
        facts["floor.miss"] = f"{round(100 * v)}%"
    near = (rec.get("baselines") or {}).get("nearest_today")
    gain = (rec.get("gain") or {}).get("vs_nearest_per_q")
    if near and gain is not None and near["kind"] == "mandi":
        facts["nearest.mandi"] = near[name_key]
        facts["gain.nearest"] = _indian(abs(gain))
        facts["gain.nearest_dir"] = {"en": "more" if gain >= 0 else "less", "kn": "ಹೆಚ್ಚು" if gain >= 0 else "ಕಡಿಮೆ",
                                     "hi": "ज़्यादा" if gain >= 0 else "कम"}[lang]
    ev = rec.get("evidence") or {}
    if ev.get("status") == "OK" and ev.get("level") == "strong" and ev["gain_vs_highest_yesterday"]["mean"] > 0:
        facts["track.days"] = str(ev["scored_days"])
        facts["track.gain"] = _indian(ev["gain_vs_highest_yesterday"]["mean"])
    if shock_item:
        a = shock_item["arrivals"]
        if a.get("direction") and a.get("age_days", 99) <= 10:
            facts["shock.state"] = STATE_WORD[a["state"]][lang]
            if a.get("times_normal"):
                facts["shock.times"] = f"{a['times_normal']:.1f}"
        g = shock_item.get("gap")
        if g and abs(g["neighbours_dearer_by_pct"]) >= 3:
            facts["gap.pct"] = f"{abs(g['neighbours_dearer_by_pct']):.0f}%"
            facts["gap.dir"] = {"en": "more" if g["neighbours_dearer_by_pct"] > 0 else "less", "kn": "ಹೆಚ್ಚು" if g["neighbours_dearer_by_pct"] > 0 else "ಕಡಿಮೆ",
                                "hi": "ज़्यादा" if g["neighbours_dearer_by_pct"] > 0 else "कम"}[lang]
            if g.get("median_half_life_weeks"):
                facts["gap.weeks"] = f"{g['median_half_life_weeks']:.0f}"
        r = shock_item.get("response")
        if r and r.get("tier") == "ROBUST":
            facts["resp.pct"] = f"{abs(r['typical_change_pct']):.0f}%"
            facts["resp.dir"] = {"en": "fell" if r["typical_change_pct"] < 0 else "rose", "kn": "ಇಳಿಯಿತು" if r["typical_change_pct"] < 0 else "ಏರಿತು",
                                 "hi": "गिरा" if r["typical_change_pct"] < 0 else "बढ़ा"}[lang]
            facts["resp.days"] = str(r["horizon_days"])
    return facts


# --------------------------------------------------------------- rule-based
def _cond(facts: Dict[str, str], *keys: str) -> bool:
    return all(k in facts for k in keys)


RULES: List[Tuple[str, Tuple[str, ...], Dict[str, str]]] = [
    ("why", ("best.net", "nearest.mandi", "gain.nearest"), {
        "en": "After transport, fees and spoilage, this should leave you {gain.nearest} per quintal {gain.nearest_dir} than going to {nearest.mandi}.",
        "kn": "ಸಾಗಣೆ, ಶುಲ್ಕ ಮತ್ತು ಹಾಳಾಗುವಿಕೆಯ ನಂತರ, {nearest.mandi} ಮಂಡಿಗೆ ಹೋಗುವುದಕ್ಕಿಂತ ಕ್ವಿಂಟಾಲ್‌ಗೆ {gain.nearest} {gain.nearest_dir} ಉಳಿಯುತ್ತದೆ.",
        "hi": "ढुलाई, शुल्क और खराबी के बाद, {nearest.mandi} मंडी जाने की तुलना में प्रति क्विंटल {gain.nearest} {gain.nearest_dir} बचना चाहिए।"}),
    ("why", ("best.open",), {
        "en": "{best.mandi} is expected to be open and trading that day, with about {best.open} chance.",
        "kn": "ಆ ದಿನ {best.mandi} ಮಂಡಿ ತೆರೆದಿರುವ ಮತ್ತು ವ್ಯಾಪಾರ ನಡೆಯುವ ಸಾಧ್ಯತೆ ಸುಮಾರು {best.open}.",
        "hi": "उस दिन {best.mandi} मंडी खुली और चालू रहने की संभावना लगभग {best.open} है।"}),
    ("why", ("gap.pct", "gap.dir"), {
        "en": "Neighbouring districts currently pay {gap.pct} {gap.dir} for {crop}.",
        "kn": "ಅಕ್ಕಪಕ್ಕದ ಜಿಲ್ಲೆಗಳಲ್ಲಿ ಈಗ {crop}ಗೆ {gap.pct} {gap.dir} ಬೆಲೆ ಇದೆ.",
        "hi": "पड़ोसी ज़िलों में अभी {crop} का भाव {gap.pct} {gap.dir} है।"}),
    ("why", ("shock.state", "shock.times"), {
        "en": "{crop} arrivals are {shock.state} ({shock.times} times normal), which usually keeps prices under pressure.",
        "kn": "{crop} ಆವಕ {shock.state} ({shock.times} ಪಟ್ಟು), ಇದು ಸಾಮಾನ್ಯವಾಗಿ ಬೆಲೆಯ ಮೇಲೆ ಒತ್ತಡ ಹಾಕುತ್ತದೆ.",
        "hi": "{crop} की आवक {shock.state} ({shock.times} गुना) है, जिससे आमतौर पर भाव पर दबाव रहता है।"}),
    ("why", ("resp.pct", "resp.dir", "resp.days"), {
        "en": "In past spikes like this, the {crop} price typically {resp.dir} by about {resp.pct} within {resp.days} days.",
        "kn": "ಹಿಂದಿನ ಇಂತಹ ಏರಿಕೆಗಳಲ್ಲಿ, {resp.days} ದಿನಗಳಲ್ಲಿ {crop} ಬೆಲೆ ಸುಮಾರು {resp.pct} {resp.dir}.",
        "hi": "पहले ऐसी बढ़ोतरी में {resp.days} दिनों के भीतर {crop} का भाव लगभग {resp.pct} {resp.dir}।"}),
    ("why", ("track.days", "track.gain"), {
        "en": "On {track.days} past days that were not used to build it, following this advice earned about {track.gain} per quintal more than going to the mandi that paid most yesterday.",
        "kn": "ಇದನ್ನು ರೂಪಿಸಲು ಬಳಸದ ಕಳೆದ {track.days} ದಿನಗಳಲ್ಲಿ, ಈ ಸಲಹೆ ಅನುಸರಿಸಿದರೆ ನಿನ್ನೆ ಹೆಚ್ಚು ಬೆಲೆ ಕೊಟ್ಟ ಮಂಡಿಗೆ ಹೋಗುವುದಕ್ಕಿಂತ ಕ್ವಿಂಟಾಲ್‌ಗೆ ಸುಮಾರು {track.gain} ಹೆಚ್ಚು ಸಿಗುತ್ತಿತ್ತು.",
        "hi": "जिन {track.days} पिछले दिनों का इस्तेमाल इसे बनाने में नहीं हुआ, उनमें इस सलाह पर चलने से कल सबसे ऊँचा भाव देने वाली मंडी जाने की तुलना में प्रति क्विंटल लगभग {track.gain} ज़्यादा मिलता।"}),
    ("caution", ("floor.miss",), {
        "en": "The minimum is a careful estimate, not a promise: in past tests it was missed about {floor.miss} of the time.",
        "kn": "ಕನಿಷ್ಠ ಮೊತ್ತ ಎಚ್ಚರಿಕೆಯ ಅಂದಾಜು, ಭರವಸೆಯಲ್ಲ: ಹಿಂದಿನ ಪರೀಕ್ಷೆಗಳಲ್ಲಿ ಅದು ಸುಮಾರು {floor.miss} ಬಾರಿ ತಪ್ಪಿತ್ತು.",
        "hi": "न्यूनतम राशि एक सावधानी भरा अनुमान है, वादा नहीं: पिछले परीक्षणों में यह लगभग {floor.miss} बार चूकी।"}),
]
CAVEAT_TEXT = {
    "limited_evidence": {"en": "Few mandis report for this crop, so treat this as a guide, not a promise.",
                         "kn": "ಈ ಬೆಳೆಗೆ ಕಡಿಮೆ ಮಂಡಿಗಳು ವರದಿ ಮಾಡುತ್ತವೆ; ಇದನ್ನು ಮಾರ್ಗದರ್ಶನವೆಂದು ಮಾತ್ರ ಪರಿಗಣಿಸಿ.",
                         "hi": "इस फसल के लिए कम मंडियाँ रिपोर्ट करती हैं; इसे मार्गदर्शन समझें, वादा नहीं।"},
    "sale_on_sunday": {"en": "That day is a Sunday and many mandis are closed; check before you go.",
                       "kn": "ಆ ದಿನ ಭಾನುವಾರ, ಅನೇಕ ಮಂಡಿಗಳು ಮುಚ್ಚಿರುತ್ತವೆ; ಹೋಗುವ ಮೊದಲು ಖಚಿತಪಡಿಸಿ.",
                       "hi": "वह दिन रविवार है और कई मंडियाँ बंद रहती हैं; जाने से पहले पता कर लें।"},
    "mandi_may_be_closed": {"en": "This mandi is often closed that day; check before you go.",
                            "kn": "ಆ ದಿನ ಈ ಮಂಡಿ ಆಗಾಗ ಮುಚ್ಚಿರುತ್ತದೆ; ಹೋಗುವ ಮೊದಲು ಖಚಿತಪಡಿಸಿ.",
                            "hi": "उस दिन यह मंडी अक्सर बंद रहती है; जाने से पहले पता कर लें।"},
    "stale_data": {"en": "The latest prices are a few days old.", "kn": "ಇತ್ತೀಚಿನ ಬೆಲೆಗಳು ಕೆಲವು ದಿನ ಹಳೆಯವು.", "hi": "ताज़ा भाव कुछ दिन पुराने हैं।"},
}
HEADLINE = {
    "en": "Sell at {best.mandi} {best.when}. Expect about {best.net} per quintal after costs, and at least {best.floor} ({floor.confidence} sure).",
    "kn": "{best.mandi} ಮಂಡಿಯಲ್ಲಿ ಮಾರಿ, {best.when}. ವೆಚ್ಚದ ನಂತರ ಕ್ವಿಂಟಾಲ್‌ಗೆ ಸುಮಾರು {best.net} ಸಿಗುತ್ತದೆ, ಕನಿಷ್ಠ {best.floor} ({floor.confidence} ಖಚಿತತೆ).",
    "hi": "{best.mandi} मंडी में बेचें, {best.when}। खर्च के बाद प्रति क्विंटल लगभग {best.net} मिलेगा, कम से कम {best.floor} ({floor.confidence} भरोसा)।",
}
HEADLINE_GATE = {
    "en": "Sell at your farm gate {best.when}. Expect about {best.net} per quintal, and at least {best.floor} ({floor.confidence} sure).",
    "kn": "ನಿಮ್ಮ ಜಮೀನಿನಲ್ಲೇ ಮಾರಿ, {best.when}. ಕ್ವಿಂಟಾಲ್‌ಗೆ ಸುಮಾರು {best.net}, ಕನಿಷ್ಠ {best.floor} ({floor.confidence} ಖಚಿತತೆ).",
    "hi": "अपने खेत पर ही बेचें, {best.when}। प्रति क्विंटल लगभग {best.net}, कम से कम {best.floor} ({floor.confidence} भरोसा)।",
}


def _fill(template: str, facts: Dict[str, str]) -> str:
    return PLACEHOLDER.sub(lambda m: facts.get(m.group(1), ""), template)


def rule_templates(facts: Dict[str, str], caveats: List[str], lang: str) -> Dict[str, List[str]]:
    """The reasons as UNRENDERED templates (placeholders intact), chosen by code from the facts available."""
    why, caution = [], []
    for kind, keys, text in RULES:
        if _cond(facts, *keys):
            (why if kind == "why" else caution).append(text[lang])
    caution += [CAVEAT_TEXT[c][lang] for c in caveats if c in CAVEAT_TEXT]
    return {"why": why[:4], "cautions": caution[:3]}


def rule_based(facts: Dict[str, str], caveats: List[str], lang: str) -> Dict[str, List[str]]:
    t = rule_templates(facts, caveats, lang)
    return {k: [_fill(x, facts) for x in v] for k, v in t.items()}


# ----------------------------------------------------------------------- LLM
SYSTEM = """You rewrite sentences for Indian farmers. Each sentence already states the right facts in the right places; \
you only make it read naturally, warmly and simply in the requested language.

Input: JSON {"sentences": [{"id": "...", "text": "..."}]}. Output: JSON {"sentences": [{"id": "...", "text": "..."}]}.

Hard rules:
1. Return every id exactly once.
2. Keep every {placeholder} exactly as written, the same number of times, wherever it keeps its meaning. Never add, remove, rename or move a placeholder to a different meaning.
3. Do not add facts, advice, reasons, comparisons or predictions. Do not change what is being claimed.
4. Never write a digit or number. Never write guarantee, certain, definitely or sure.
5. Use the requested language and script only. At most 30 words per sentence."""


def _script_ok(text: str, lang: str) -> bool:
    if lang == "en":
        return not any(ord(ch) > 0x024F for ch in text if ch.isalpha())
    lo, hi = SCRIPT_RANGE[lang]
    letters = [ch for ch in re.sub(r"\{[^}]*\}", "", text) if ch.isalpha()]
    return bool(letters) and sum(lo <= ord(ch) <= hi for ch in letters) / len(letters) >= 0.6


def validate_paraphrase(source: str, new: str, lang: str) -> Optional[str]:
    """None if `new` is an acceptable paraphrase of `source`, else the reason it was rejected."""
    if not isinstance(new, str) or not new.strip():
        return "empty"
    if sorted(PLACEHOLDER.findall(source)) != sorted(PLACEHOLDER.findall(new)):
        return "placeholders_changed"
    if re.search(r"[{}]", PLACEHOLDER.sub("", new)):
        return "malformed_placeholder"
    if DIGITS.search(PLACEHOLDER.sub("", new)):
        return "contains_digit"
    if OVERCLAIM.search(new):
        return "overclaim"
    if len(new.split()) > MAX_WORDS:
        return "too_long"
    if not _script_ok(new, lang):
        return "wrong_language"
    return None


def _llm_json(system: str, user: str, model: Optional[str] = None) -> Tuple[Dict[str, Any], str]:
    import httpx

    load_env()
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set")
    model = model or os.getenv("MANDISENSE_GROQ_MODEL", "openai/gpt-oss-120b")
    body = {"model": model, "temperature": 0.2, "max_tokens": 1500, "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    if "gpt-oss" in model:
        body["reasoning_effort"] = "low"
    from mandisense_ai.chat.providers import RATE_LIMIT_MAX_WAIT, RATE_LIMIT_RETRIES, _reset_seconds

    def post():
        return httpx.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {key}"}, json=body, timeout=45)

    r = post()
    if r.status_code == 400 and "reasoning_effort" in body:
        body.pop("reasoning_effort")
        r = post()
    for _ in range(RATE_LIMIT_RETRIES):                      # per-minute token budget: wait for it to refill rather than give up
        wait = _reset_seconds(r.headers) if r.status_code == 429 else None
        if wait is None or wait > RATE_LIMIT_MAX_WAIT:
            break
        time.sleep(wait + 0.5)
        r = post()
    if r.status_code != 200:
        raise RuntimeError(f"Groq API error {r.status_code}: {r.text[:200]}")
    text = r.json()["choices"][0]["message"]["content"] or ""
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0) if m else text), model


LANG_NAME = {"en": "English", "kn": "Kannada (ಕನ್ನಡ script)", "hi": "Hindi (देवनागरी script)"}


JUDGE_SYSTEM = """You check whether a rewritten sentence says exactly the same thing as the original, for a farming advice app.
The ORIGINAL is correct. The REWRITE is in another wording or language and may contain the same {placeholders}.

For each pair answer whether the REWRITE is faithful. It is NOT faithful if it:
- reverses a direction or comparison (more/less, higher/lower, cheaper/dearer, rises/falls, open/closed);
- adds a claim, reason, advice or prediction that the ORIGINAL does not make;
- drops a claim the ORIGINAL makes (for example that something was not used to build the model);
- attaches a placeholder to a different meaning than in the ORIGINAL;
- is garbled or ungrammatical enough that a farmer could misread it.

Input: JSON {"pairs": [{"id": "...", "original": "...", "rewrite": "..."}]}
Output: JSON {"results": [{"id": "...", "faithful": true|false, "problem": "short reason, empty if faithful"}]}"""


def judge_faithful(pairs: List[Dict[str, str]], lang: str, model: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """Independent meaning check of paraphrases against their sources. Missing verdicts count as unfaithful."""
    if not pairs:
        return {}
    model = model or os.getenv("MANDISENSE_JUDGE_MODEL", "openai/gpt-oss-120b")
    raw, _ = _llm_json(JUDGE_SYSTEM, f"Rewrite language: {LANG_NAME[lang]}\n" + json.dumps({"pairs": pairs}, ensure_ascii=False), model)
    return {str(r.get("id")): {"faithful": bool(r.get("faithful")), "problem": str(r.get("problem", ""))[:140]}
            for r in (raw.get("results") or []) if isinstance(r, dict)}


def llm_explain(base: Dict[str, List[str]], facts: Dict[str, str], lang: str, model: Optional[str] = None, judge: bool = True,
                judge_model: Optional[str] = None) -> Dict[str, Any]:
    """Paraphrase the rule-based sentences. `base` holds UNRENDERED templates under 'why' and 'cautions'."""
    items = [{"id": f"{kind[0]}{i}", "text": t} for kind in ("why", "cautions") for i, t in enumerate(base[kind])]
    if not items:
        raise RuntimeError("nothing to paraphrase")
    user = f"Language: {LANG_NAME[lang]}\n" + json.dumps({"sentences": items}, ensure_ascii=False)
    t0 = time.time()
    raw, used = _llm_json(SYSTEM, user, model)
    got = {str(x.get("id")): x.get("text") for x in (raw.get("sentences") or []) if isinstance(x, dict)}
    out = {"why": [], "cautions": []}
    rejected: List[Dict[str, str]] = []
    n_llm = 0
    verdict: Dict[str, Dict[str, Any]] = {}
    checked = {f"{k[0]}{i}": (src, got.get(f"{k[0]}{i}")) for k in ("why", "cautions") for i, src in enumerate(base[k])}
    passed = {i: (src, new) for i, (src, new) in checked.items() if new is not None and not validate_paraphrase(src, new, lang)}
    if judge and passed:
        try:
            verdict = judge_faithful([{"id": i, "original": src, "rewrite": new} for i, (src, new) in passed.items()], lang, judge_model)
        except Exception as exc:  # no verdict means no trust: keep the rule-based wording
            logger.warning("Faithfulness judge failed (%s); keeping rule-based sentences", exc)
    for kind in ("why", "cautions"):
        for i, src in enumerate(base[kind]):
            sid = f"{kind[0]}{i}"
            new = got.get(sid)
            reason = validate_paraphrase(src, new, lang) if new is not None else "missing"
            if not reason and judge and not verdict.get(sid, {}).get("faithful"):
                reason = "judge:" + (verdict.get(sid, {}).get("problem") or "no verdict")
            if reason:
                rejected.append({"source": src[:100], "rewrite": (new or "")[:100], "reason": reason})
                out[kind].append(_fill(src, facts))
            else:
                out[kind].append(_fill(new, facts))
                n_llm += 1
    return {**out, "rejected": rejected, "model": used, "latency_ms": round(1000 * (time.time() - t0)), "n_sentences": len(items), "n_llm": n_llm}


# ------------------------------------------------------------------ orchestrate
_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
TTL = 1800


def explain(rec: Dict[str, Any], shock_item: Optional[Dict[str, Any]], lang: str = "en", use_llm: bool = True,
            model: Optional[str] = None) -> Dict[str, Any]:
    load_env()
    lang = lang if lang in LANGS else "en"
    facts = build_facts(rec, shock_item, lang)
    caveats = rec.get("caveats") or []
    best = rec["recommended"]
    headline = _fill((HEADLINE_GATE if best["kind"] == "farm_gate" else HEADLINE)[lang], facts)
    base = rule_based(facts, caveats, lang)
    out: Dict[str, Any] = {"lang": lang, "headline": headline, "why": base["why"], "cautions": base["cautions"],
                           "author": "rules", "model": None, "checks": {"numbers_inserted_by_code": True, "decision_unchanged": True}}
    key = f"{rec['crop']}|{rec.get('origin', {}).get('lat')}|{rec.get('quantity_quintals')}|{rec.get('alpha')}|{rec.get('decision_day')}|{lang}|{model}"
    if use_llm and os.getenv("GROQ_API_KEY", "").strip():
        hit = _CACHE.get(key)
        if hit and time.time() - hit[0] < TTL:
            return hit[1]
        try:
            got = llm_explain(rule_templates(facts, caveats, lang), facts, lang, model)
            out.update({"why": got["why"], "cautions": got["cautions"], "author": "llm" if got["n_llm"] else "rules", "model": got["model"]})
            out["checks"].update({"sentences": got["n_sentences"], "sentences_by_llm": got["n_llm"], "rejected": got["rejected"],
                                  "latency_ms": got["latency_ms"]})
            _CACHE[key] = (time.time(), out)
        except Exception as exc:
            logger.warning("LLM explanation failed (%s); using rule-based", exc)
            out["checks"]["llm_error"] = str(exc)[:160]
    return out
