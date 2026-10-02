"""
The tool-driven answerer: what the chatbots do when no hosted LLM is configured
(or when it fails).

It is not a canned-reply bot. Each question is routed (in English, Kannada or
Hindi) to the real tools, and the answer is written from the tool results in
the user's language. Anything the records cannot answer goes to the live web.
Every number in a reply comes straight from a tool result.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from mandisense_ai.chat.entities import Entities, crop_name, place_name
from mandisense_ai.chat.languages import normalise_digits
from mandisense_ai.chat.translate import translate

Run = Callable[[str, Dict[str, Any]], Dict[str, Any]]


@dataclass
class Fallback:
    text: str
    intent: str
    sources: List[Dict[str, str]] = field(default_factory=list)


def _t(lang: str, en: str, kn: str, hi: str) -> str:
    return {"kn": kn, "hi": hi}.get(lang, en)


def inr(n: Optional[float]) -> str:
    """Rupees with Indian digit grouping: 147230 -> ₹1,47,230."""
    if n is None:
        return "—"
    s = f"{abs(round(float(n))):d}"
    head, tail = s[:-3], s[-3:]
    if head:
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts) + "," + tail
    return ("−" if n < 0 else "") + "₹" + s


def sinr(n: Optional[float]) -> str:
    if n is None:
        return "—"
    return ("+" if n >= 0 else "") + inr(n)


# ── intent routing ──────────────────────────────────────────────────────────

def _has(text: str, words: List[str]) -> bool:
    return any(w in text for w in words)


W = {
    "help": ["hello", "hi ", "hey", "help", "namaste", "what can you", "ನಮಸ್ಕಾರ", "ಸಹಾಯ", "ಹಲೋ", "नमस्ते", "मदद", "हेलो", "नमस्कार"],
    "weather": ["weather", "rain", "temperature", "monsoon", "ಮಳೆ", "ಹವಾಮಾನ", "ತಾಪಮಾನ", "बारिश", "मौसम", "तापमान"],
    "web": ["msp", "support price", "scheme", "subsid", "fertili", "pesticide", "pest", "disease", "insurance", "loan", "news",
            "export", "import", "tariff", "policy", "kisan", "ಕಿಸಾನ್", "किसान", "ಪಿಎಂ", "पीएम", "pm-kisan", "organic", "seed", "irrigation",
            "ಬೆಂಬಲ ಬೆಲೆ", "ಗೊಬ್ಬರ", "ಕೀಟ", "ರೋಗ", "ವಿಮೆ", "ಸಾಲ", "ಸಬ್ಸಿಡಿ", "ಸುದ್ದಿ", "ರಫ್ತು", "ಬೀಜ", "ನೀರಾವರಿ",
            "समर्थन मूल्य", "खाद", "कीट", "रोग", "बीमा", "ऋण", "सब्सिडी", "समाचार", "निर्यात", "बीज", "सिंचाई"],
    "accuracy": ["accura", "trust", "reliable", "how often", "right", "ನಿಖರ", "ನಂಬ", "ಎಷ್ಟು ಬಾರಿ", "सटीक", "भरोसा", "कितनी बार"],
    "seasonal": ["last year", "same time", "this time", "seasonal", "ಕಳೆದ ವರ್ಷ", "ಹಿಂದಿನ ವರ್ಷ", "पिछले साल", "पिछले वर्ष"],
    "supply": ["arrival", "supply", "glut", "shortage", "ಆವಕ", "ಪೂರೈಕೆ", "आवक", "सप्लाई", "आपूर्ति"],
    "where": ["where", "which mandi", "best mandi", "nearby", "nearest", "ಎಲ್ಲಿ", "ಯಾವ ಮಂಡಿ", "ಹತ್ತಿರ", "कहाँ", "कहां", "कौन सी मंडी", "नज़दीक"],
    "sell": ["hold", "wait", "store", "keep", "sell", "should i", "plan", "load", "ಕಾಯ", "ಮಾರ", "ಹಿಡಿ", "ಸಂಗ್ರ", "ಯೋಜನೆ", "रुक", "बेच", "रोक", "योजना"],
    "price": ["price", "rate", "worth", "cost", "value", "how much", "ಬೆಲೆ", "ದರ", "ಎಷ್ಟು", "भाव", "कीमत", "दाम", "रेट"],
    # trader
    "spread": ["spread", "arbitrage", "margin", "route", "ಅಂತರ", "ಲಾಭ", "अंतर", "मार्जिन"],
    "gap": ["gap", "district gap", "ಅಂತರ ಜಿಲ್ಲೆ"],
    "vol": ["volatil", "regime", "turbulent", "calm", "ಅಸ್ಥಿರ", "ಏರಿಳಿತ", "अस्थिर", "उतार"],
    "analog": ["analog", "similar", "precedent", "looked like", "history like", "ಹೋಲಿಕೆ", "समान", "मिलता"],
    "scenario": ["scenario", "shock", "what if", "surge", "ಸನ್ನಿವೇಶ", "परिदृश्य", "अगर"],
    "forward": ["forward", "fair price", "hedge", "future price", "contract", "ಮುಂದಿನ ಬೆಲೆ", "वायदा", "आगे का भाव"],
    "transmission": ["transmission", "spillover", "cross-commodity", "cross commodity", "link between", "ಪ್ರಸರಣ", "संचरण"],
    "brief": ["brief", "recommend", "should i buy", "decision", "advice", "ಶಿಫಾರಸು", "सिफारिश", "निर्णय"],
}


_STRONG_SELL = ["hold", "wait", "sell", "store", "keep", "should i", "ಕಾಯ", "ಮಾರ", "ಹಿಡಿ", "ಸಂಗ್ರ", "रुक", "बेच", "रोक"]
_WEAK_SELL = ["plan", "load", "ಯೋಜನೆ", "योजना"]
_GREETING_ONLY = 5  # words


def route(persona: str, text: str, ent: Entities, current: Optional[Entities] = None) -> str:
    """Pick the intent. `current` is what THIS message named; `ent` also includes
    what was carried from earlier turns, so a bare greeting never reuses a crop."""
    t = normalise_digits(text).lower()
    cur = current or ent
    short = len(t.split()) <= _GREETING_ONLY
    if _has(t, W["weather"]):
        return "weather"
    if _has(t, W["help"]) and short and not cur.crop:
        return "help"
    if _has(t, W["web"]) and not (cur.crop and _has(t, W["price"])):
        return "web"
    if persona == "trader":
        for key, intent in (("transmission", "transmission"), ("gap", "gap"), ("forward", "forward"), ("scenario", "scenario"),
                            ("analog", "analog"), ("vol", "vol"), ("spread", "spread"), ("brief", "brief")):
            if _has(t, W[key]):
                return intent
    else:
        if _has(t, W["accuracy"]) and not cur.crop:
            return "accuracy"
        if _has(t, W["seasonal"]):
            return "seasonal"
        if _has(t, W["supply"]):
            return "supply"
        if _has(t, W["where"]):
            return "where"
        if _has(t, _STRONG_SELL) and ent.crop:
            return "sell"
        if _has(t, _WEAK_SELL) and ent.crop and ent.quantity_quintals:
            return "sell"
    if cur.crop:
        return "price"
    if ent.crop and _has(t, W["price"]):
        return "price"
    if _has(t, W["price"]):
        return "clarify"
    return "web"


# ── renderers ───────────────────────────────────────────────────────────────

_CONF = {"LOW": ("low", "ಕಡಿಮೆ", "कम"), "MEDIUM": ("medium", "ಮಧ್ಯಮ", "मध्यम"), "HIGH": ("high", "ಹೆಚ್ಚು", "उच्च"),
         "INSUFFICIENT_EVIDENCE": ("insufficient evidence", "ಸಾಕಷ್ಟು ಪುರಾವೆ ಇಲ್ಲ", "पर्याप्त प्रमाण नहीं")}


def _conf(value: str, lang: str) -> str:
    row = _CONF.get(str(value).upper())
    return row[{"en": 0, "kn": 1, "hi": 2}[lang]] if row else str(value).lower()


_ACTION = {"SELL": ("SELL", "ಮಾರಿ", "बेच दें"), "HOLD": ("HOLD", "ಹಿಡಿದಿಡಿ", "रोकें"), "WAIT": ("WAIT", "ಕಾಯಿರಿ", "रुकें")}


def _action(a: str, lang: str) -> str:
    row = _ACTION.get(str(a).upper())
    return row[{"en": 0, "kn": 1, "hi": 2}[lang]] if row else str(a)


def _unavailable(lang: str, what: str = "") -> str:
    return _t(lang, "I don't have a recent record for that in the mandi data.",
              "ಇದಕ್ಕೆ ಮಂಡಿ ದಾಖಲೆಗಳಲ್ಲಿ ಇತ್ತೀಚಿನ ಮಾಹಿತಿ ನನ್ನ ಬಳಿ ಇಲ್ಲ.",
              "इसके लिए मंडी रिकॉर्ड में मेरे पास हाल की जानकारी नहीं है।")


def _assumed(lang: str, place: str, assumed: bool) -> str:
    if not assumed:
        return ""
    return "\n" + _t(lang, f"(I used {place}. Tell me another place if you want that instead.)",
                     f"({place} ಬಳಸಿದ್ದೇನೆ. ಬೇರೆ ಸ್ಥಳ ಬೇಕಿದ್ದರೆ ಹೇಳಿ.)",
                     f"({place} इस्तेमाल किया है। दूसरी जगह चाहिए तो बताइए।)")


def _call_text(call: Dict[str, Any], lang: str) -> str:
    kind = call.get("type")
    h = call.get("horizon")
    if kind == "ADVISED" and call.get("decision") == "SELL":
        return _t(lang, f"Recommendation: SELL. The record supports selling within {h} days.",
                  f"ಸಲಹೆ: ಮಾರಿ. ದಾಖಲೆಯ ಪ್ರಕಾರ {h} ದಿನಗಳಲ್ಲಿ ಮಾರುವುದು ಒಳ್ಳೆಯದು.",
                  f"सलाह: बेच दें। रिकॉर्ड के अनुसार {h} दिनों के भीतर बेचना ठीक है।")
    if kind == "ADVISED":
        return _t(lang, f"Recommendation: HOLD. Prices may rise over the next {h} days.",
                  f"ಸಲಹೆ: ಹಿಡಿದಿಡಿ. ಮುಂದಿನ {h} ದಿನಗಳಲ್ಲಿ ಬೆಲೆ ಏರುವ ಸಾಧ್ಯತೆ ಇದೆ.",
                  f"सलाह: रोकें। अगले {h} दिनों में भाव बढ़ सकते हैं।")
    if kind == "ABSTAINED":
        return _t(lang, "No clear call: the signals are balanced, so I won't push you to sell or hold.",
                  "ಸ್ಪಷ್ಟ ಸಲಹೆ ಇಲ್ಲ: ಸೂಚನೆಗಳು ಸಮತೋಲನದಲ್ಲಿವೆ, ಹಾಗಾಗಿ ಮಾರಲು ಅಥವಾ ಹಿಡಿಯಲು ಒತ್ತಾಯಿಸುವುದಿಲ್ಲ.",
                  "कोई साफ़ सलाह नहीं: संकेत संतुलित हैं, इसलिए बेचने या रोकने का दबाव नहीं देता।")
    return _t(lang, "I don't give a sell-or-hold call for this crop yet: the record hasn't proved it can beat a simple \"no change\" guess here. Use the price and range as a guide.",
              "ಈ ಬೆಳೆಗೆ ಇನ್ನೂ ಮಾರುವ-ಹಿಡಿಯುವ ಸಲಹೆ ನೀಡುವುದಿಲ್ಲ: \"ಬೆಲೆ ಬದಲಾಗುವುದಿಲ್ಲ\" ಎಂಬ ಸರಳ ಊಹೆಯನ್ನು ಇಲ್ಲಿ ಮೀರಿಸಬಲ್ಲದು ಎಂದು ದಾಖಲೆ ಇನ್ನೂ ಸಾಬೀತುಪಡಿಸಿಲ್ಲ. ಬೆಲೆ ಮತ್ತು ಶ್ರೇಣಿಯನ್ನು ಮಾರ್ಗದರ್ಶಿಯಾಗಿ ಬಳಸಿ.",
              "इस फसल के लिए अभी बेचने-रोकने की सलाह नहीं देता: रिकॉर्ड ने अभी साबित नहीं किया कि वह \"भाव नहीं बदलेगा\" जैसे सरल अनुमान को यहाँ हरा सकता है। भाव और दायरे को मार्गदर्शन की तरह लें।")


def _mname(m: Dict[str, Any], lang: str, key: str = "mandi_name") -> str:
    return str(m.get({"kn": f"{key}_kn", "hi": f"{key}_hi"}.get(lang, key)) or m.get(key) or m.get("name") or m.get("id") or "")


def _render_price(b: Dict[str, Any], ent: Entities, lang: str, assumed: bool) -> str:
    crop, place = crop_name(b["crop"], lang), place_name(b["district"], lang)
    price, d7 = b["price_per_quintal"], (b.get("change_pct") or {}).get("d7")
    lines = [_t(lang, f"{crop} in {place}: {inr(price)} per quintal (as of {b['price_date']}).",
                f"{place}ದಲ್ಲಿ {crop}: ಕ್ವಿಂಟಾಲ್‌ಗೆ {inr(price)} ({b['price_date']} ರಂತೆ).",
                f"{place} में {crop}: {inr(price)} प्रति क्विंटल ({b['price_date']} तक)।")]
    if d7 is not None:
        up = d7 >= 0
        lines.append(_t(lang, f"Over the last 7 days the price {'rose' if up else 'fell'} {abs(d7):.1f}%.",
                        f"ಕಳೆದ 7 ದಿನಗಳಲ್ಲಿ ಬೆಲೆ {abs(d7):.1f}% {'ಏರಿದೆ' if up else 'ಇಳಿದಿದೆ'}.",
                        f"पिछले 7 दिनों में भाव {abs(d7):.1f}% {'बढ़ा' if up else 'घटा'} है।"))
    lines.append(_call_text(b["call"], lang))
    row = next((r for h in (3, 5, 7, 1) for r in b.get("forecast", []) if r["horizon"] == h and r.get("p05") and r.get("p95")), None)
    if row:
        h = row["horizon"]
        lines.append(_t(lang, f"Likely range in {h} days: {inr(row['p05'])} to {inr(row['p95'])}.",
                        f"{h} ದಿನಗಳಲ್ಲಿ ಸಂಭವನೀಯ ಬೆಲೆ ಶ್ರೇಣಿ: {inr(row['p05'])} ರಿಂದ {inr(row['p95'])}.",
                        f"{h} दिनों में संभावित भाव: {inr(row['p05'])} से {inr(row['p95'])}।"))
    live = [m for m in b.get("mandis_today", []) if m["arrivals_tonnes"] >= 1]
    if live:
        prices = sorted(m["price"] for m in live)
        median = prices[len(prices) // 2]
        top = max((m for m in live if m["price"] <= median * 1.5), key=lambda m: m["price"], default=None)
        if top:
            tn = {"kn": top.get("mandi_kn"), "hi": top.get("mandi_hi")}.get(lang) or top["mandi"]
            lines.append(_t(lang, f"Highest price among mandis today: {top['mandi']} at {inr(top['price'])}.",
                            f"ಇಂದು ಮಂಡಿಗಳಲ್ಲಿ ಹೆಚ್ಚು ಬೆಲೆ: {tn} — {inr(top['price'])}.",
                            f"आज मंडियों में सबसे ज़्यादा भाव: {tn} — {inr(top['price'])}।"))
    loss = b.get("daily_loss_pct")
    if loss and (b.get("shelf_life_days") or 99) <= 7:
        lines.append(_t(lang, f"Note: {crop} loses about {loss:g}% of its value a day in storage.",
                        f"ಸೂಚನೆ: {crop} ಸಂಗ್ರಹದಲ್ಲಿ ದಿನಕ್ಕೆ ಸುಮಾರು {loss:g}% ಮೌಲ್ಯ ಕಳೆದುಕೊಳ್ಳುತ್ತದೆ.",
                        f"ध्यान दें: {crop} भंडारण में रोज़ लगभग {loss:g}% मूल्य खो देता है।"))
    return "\n".join(lines) + _assumed(lang, place, assumed)


def _render_hold(r: Dict[str, Any], crop: str, qty: float, lang: str) -> str:
    opts = r.get("options") or []
    if r.get("status") != "OK" or not opts:
        return _unavailable(lang)
    now = r["sell_today_value"]
    best = max(opts, key=lambda o: o["net_value"])
    gain, h = best["net_value"] - now, best["horizon_days"]
    head = _t(lang, f"Selling {qty:g} quintals of {crop} today gives about {inr(now)}.",
              f"{qty:g} ಕ್ವಿಂಟಾಲ್ {crop} ಇಂದೇ ಮಾರಿದರೆ ಸುಮಾರು {inr(now)} ಸಿಗುತ್ತದೆ.",
              f"{qty:g} क्विंटल {crop} आज बेचने पर लगभग {inr(now)} मिलेंगे।")
    if gain > 0:
        tail = _t(lang, f"Waiting {h} days could add about {inr(gain)} after spoilage, but that depends on the forecast. Lean: HOLD.",
                  f"{h} ದಿನ ಕಾದರೆ ಹಾಳಾಗುವಿಕೆ ಕಳೆದ ನಂತರ ಸುಮಾರು {inr(gain)} ಹೆಚ್ಚು ಸಿಗಬಹುದು, ಆದರೆ ಅದು ಮುನ್ಸೂಚನೆಯ ಮೇಲೆ ಅವಲಂಬಿತ. ಸಲಹೆ: ಹಿಡಿದಿಡಿ.",
                  f"{h} दिन रुकने पर खराबी घटाकर लगभग {inr(gain)} ज़्यादा मिल सकते हैं, पर यह अनुमान पर निर्भर है। सलाह: रोकें।")
    else:
        tail = _t(lang, f"Waiting {h} days would leave you about {inr(abs(gain))} worse off after spoilage. Lean: SELL now.",
                  f"{h} ದಿನ ಕಾದರೆ ಹಾಳಾಗುವಿಕೆಯಿಂದ ಸುಮಾರು {inr(abs(gain))} ನಷ್ಟವಾಗುತ್ತದೆ. ಸಲಹೆ: ಈಗಲೇ ಮಾರಿ.",
                  f"{h} दिन रुकने पर खराबी से लगभग {inr(abs(gain))} का नुकसान होगा। सलाह: अभी बेचें।")
    return head + "\n" + tail


def _render_plan(r: Dict[str, Any], crop: str, qty: float, lang: str) -> str:
    if r.get("status") != "OK":
        return _unavailable(lang)
    best = next(o for o in r["options"] if o["choice"] == r["best"])
    here = r["options"][0]
    mn = _mname(best, lang)
    if best["choice"] == "sell_today":
        body = _t(lang, f"sell today at {mn} for about {inr(best['total'])}.",
                  f"ಇಂದೇ {mn}ದಲ್ಲಿ ಮಾರಿ, ಸುಮಾರು {inr(best['total'])} ಸಿಗುತ್ತದೆ.",
                  f"आज {mn} में बेचें, लगभग {inr(best['total'])} मिलेंगे।")
    elif best["choice"] == "travel":
        body = _t(lang, f"take it to {mn} ({best['distance_km']:g} km): about {inr(best['total'])} after transport, {inr(r['gain_vs_baseline'])} more than selling at home.",
                  f"{mn}ಗೆ ({best['distance_km']:g} ಕಿ.ಮೀ) ಕೊಂಡೊಯ್ಯಿರಿ: ಸಾಗಣೆ ಕಳೆದು ಸುಮಾರು {inr(best['total'])}, ಊರಿನಲ್ಲಿ ಮಾರುವುದಕ್ಕಿಂತ {inr(r['gain_vs_baseline'])} ಹೆಚ್ಚು.",
                  f"{mn} ले जाएँ ({best['distance_km']:g} किमी): ढुलाई घटाकर लगभग {inr(best['total'])}, घर पर बेचने से {inr(r['gain_vs_baseline'])} ज़्यादा।")
    else:
        body = _t(lang, f"wait until {best['target_date']}: about {inr(best['total'])} after spoilage, {inr(r['gain_vs_baseline'])} more than today.",
                  f"{best['target_date']} ವರೆಗೆ ಕಾಯಿರಿ: ಹಾಳಾಗುವಿಕೆ ಕಳೆದು ಸುಮಾರು {inr(best['total'])}, ಇಂದಿಗಿಂತ {inr(r['gain_vs_baseline'])} ಹೆಚ್ಚು.",
                  f"{best['target_date']} तक रुकें: खराबी घटाकर लगभग {inr(best['total'])}, आज से {inr(r['gain_vs_baseline'])} ज़्यादा।")
    head = _t(lang, f"Best for {qty:g} quintals of {crop}: ", f"{qty:g} ಕ್ವಿಂಟಾಲ್ {crop}ಗೆ ಉತ್ತಮ: ", f"{qty:g} क्विंटल {crop} के लिए सबसे अच्छा: ")
    base = _t(lang, f"Selling at home today: about {inr(here['total'])}.", f"ಊರಿನಲ್ಲಿ ಇಂದು ಮಾರಿದರೆ: ಸುಮಾರು {inr(here['total'])}.", f"घर पर आज बेचने पर: लगभग {inr(here['total'])}।")
    return head + body + "\n" + base + "\n" + _call_text(r["call"], lang)


def _render_where(r: Dict[str, Any], crop: str, lang: str) -> str:
    rows = [m for m in r.get("mandis", []) if not m.get("outlier") and not m.get("thin_for_load")] or r.get("mandis", [])
    if r.get("status") != "OK" or not rows:
        return _unavailable(lang)
    rows = sorted(rows, key=lambda m: -m["net_total"])[:3]
    head = _t(lang, f"Best mandis for {crop} after transport:", f"ಸಾಗಣೆ ವೆಚ್ಚ ಕಳೆದ ನಂತರ {crop}ಗೆ ಉತ್ತಮ ಮಂಡಿಗಳು:", f"ढुलाई के बाद {crop} के लिए सबसे अच्छी मंडियाँ:")
    out = [head]
    for m in rows:
        out.append(_t(lang, f"• {_mname(m, lang)}: {inr(m['net_price_per_quintal'])} per quintal after transport ({m['distance_km']:g} km)",
                      f"• {_mname(m, lang)}: ಸಾಗಣೆ ಕಳೆದು ಕ್ವಿಂಟಾಲ್‌ಗೆ {inr(m['net_price_per_quintal'])} ({m['distance_km']:g} ಕಿ.ಮೀ)",
                      f"• {_mname(m, lang)}: ढुलाई के बाद {inr(m['net_price_per_quintal'])} प्रति क्विंटल ({m['distance_km']:g} किमी)"))
    return "\n".join(out)


def _render_seasonal(r: Dict[str, Any], crop: str, lang: str) -> str:
    ly, norm = r.get("last_year"), r.get("seasonal_norm")
    if r.get("status") != "OK" or not ly:
        return _unavailable(lang)
    ch = ly["change_pct"]
    cur = r["current_price"]
    lines = [_t(lang, f"A year ago ({ly['date']}) {crop} was {inr(ly['price'])}; today it is {inr(cur)}, {abs(ch):.1f}% {'higher' if ch >= 0 else 'lower'}.",
                f"ಒಂದು ವರ್ಷದ ಹಿಂದೆ ({ly['date']}) {crop} {inr(ly['price'])} ಇತ್ತು; ಇಂದು {inr(cur)}, ಅಂದರೆ {abs(ch):.1f}% {'ಹೆಚ್ಚು' if ch >= 0 else 'ಕಡಿಮೆ'}.",
                f"एक साल पहले ({ly['date']}) {crop} {inr(ly['price'])} था; आज {inr(cur)} है, यानी {abs(ch):.1f}% {'ज़्यादा' if ch >= 0 else 'कम'}।")]
    if norm:
        dev = norm["deviation_pct"]
        lines.append(_t(lang, f"Against the usual price for this season ({inr(norm['median_price'])}), today is {abs(dev):.1f}% {'above' if dev >= 0 else 'below'}.",
                        f"ಈ ಋತುವಿನ ಸಾಮಾನ್ಯ ಬೆಲೆ ({inr(norm['median_price'])}) ಗೆ ಹೋಲಿಸಿದರೆ ಇಂದು {abs(dev):.1f}% {'ಹೆಚ್ಚು' if dev >= 0 else 'ಕಡಿಮೆ'}.",
                        f"इस मौसम के सामान्य भाव ({inr(norm['median_price'])}) की तुलना में आज {abs(dev):.1f}% {'ऊपर' if dev >= 0 else 'नीचे'} है।"))
    return "\n".join(lines)


def _render_supply(r: Dict[str, Any], crop: str, lang: str) -> str:
    if r.get("status") != "OK":
        return _unavailable(lang)
    dev, latest, base = r["deviation_pct"], r["latest_arrivals"], r["baseline_arrivals"]
    high = dev >= 0
    return _t(lang,
              f"Arrivals of {crop} are {abs(dev):.0f}% {'above' if high else 'below'} normal ({latest:g} vs {base:g} tonnes), {'a glut that can push prices down' if high else 'thin supply that can support prices'}.",
              f"{crop} ಆವಕ ಸಾಮಾನ್ಯಕ್ಕಿಂತ {abs(dev):.0f}% {'ಹೆಚ್ಚು' if high else 'ಕಡಿಮೆ'} ({latest:g} ಟನ್, ಸಾಮಾನ್ಯ {base:g} ಟನ್); {'ಇದು ಬೆಲೆಯನ್ನು ಇಳಿಸಬಹುದು' if high else 'ಇದು ಬೆಲೆಗೆ ಬೆಂಬಲ ನೀಡಬಹುದು'}.",
              f"{crop} की आवक सामान्य से {abs(dev):.0f}% {'ज़्यादा' if high else 'कम'} है ({latest:g} टन, सामान्य {base:g} टन); {'इससे भाव गिर सकते हैं' if high else 'इससे भाव को सहारा मिल सकता है'}।")


def _render_accuracy(r: Dict[str, Any], lang: str) -> str:
    o = r.get("overall") or {}
    if not o:
        return _unavailable(lang)
    n, dr = o["forecasts"], o["direction_right"] * 100
    return _t(lang, f"Tested on {n:,} forecasts for weeks the model had never seen, the direction was right {dr:.0f}% of the time. Prices stay hard to predict, so treat advice as guidance, not a guarantee.",
              f"ಮಾದರಿ ಹಿಂದೆಂದೂ ನೋಡದ ವಾರಗಳ {n:,} ಮುನ್ಸೂಚನೆಗಳ ಮೇಲೆ ಪರೀಕ್ಷಿಸಿದಾಗ, ದಿಕ್ಕು {dr:.0f}% ಬಾರಿ ಸರಿಯಾಗಿತ್ತು. ಬೆಲೆ ಊಹಿಸುವುದು ಕಷ್ಟ; ಸಲಹೆ ಮಾರ್ಗದರ್ಶನ ಮಾತ್ರ, ಖಾತರಿಯಲ್ಲ.",
              f"मॉडल ने जो हफ़्ते कभी नहीं देखे, उनके {n:,} पूर्वानुमानों पर दिशा {dr:.0f}% बार सही रही। भाव का अनुमान कठिन है; सलाह मार्गदर्शन है, गारंटी नहीं।")


_WX = {"clear": ("ಸ್ವಚ್ಛ", "साफ़"), "mostly clear": ("ಬಹುತೇಕ ಸ್ವಚ್ಛ", "ज़्यादातर साफ़"), "partly cloudy": ("ಭಾಗಶಃ ಮೋಡ", "आंशिक बादल"),
       "overcast": ("ಮೋಡ ಕವಿದಿದೆ", "बादल छाए"), "fog": ("ಮಂಜು", "कोहरा"), "light drizzle": ("ತುಂತುರು", "हल्की बूंदाबांदी"),
       "drizzle": ("ತುಂತುರು", "बूंदाबांदी"), "heavy drizzle": ("ಜೋರು ತುಂತುರು", "तेज़ बूंदाबांदी"), "light rain": ("ಹಗುರ ಮಳೆ", "हल्की बारिश"),
       "rain": ("ಮಳೆ", "बारिश"), "heavy rain": ("ಭಾರೀ ಮಳೆ", "भारी बारिश"), "rain showers": ("ಮಳೆ ಹನಿಗಳು", "बारिश की बौछारें"),
       "violent rain showers": ("ಭಾರೀ ಮಳೆ", "तेज़ बौछारें"), "thunderstorm": ("ಗುಡುಗು ಸಹಿತ ಮಳೆ", "आंधी-तूफ़ान"),
       "thunderstorm with hail": ("ಗುಡುಗು, ಆಲಿಕಲ್ಲು", "आंधी, ओले"), "mixed": ("ಮಿಶ್ರ", "मिला-जुला")}


def _render_weather(r: Dict[str, Any], lang: str, local_place: str = "") -> str:
    if r.get("error") or not r.get("days"):
        return _t(lang, "I couldn't get the weather right now.", "ಈಗ ಹವಾಮಾನ ಮಾಹಿತಿ ಪಡೆಯಲು ಆಗಲಿಲ್ಲ.", "अभी मौसम की जानकारी नहीं मिल सकी।")
    pl = local_place or r["place"]
    out = [_t(lang, f"Weather for {pl}:", f"{pl} ಹವಾಮಾನ:", f"{pl} का मौसम:")]
    for d in r["days"]:
        kn, hi = _WX.get(d["summary"], (d["summary"], d["summary"]))
        s = {"kn": kn, "hi": hi}.get(lang, d["summary"])
        out.append(_t(lang, f"• {d['date']}: {d['min_c']:g}–{d['max_c']:g}°C, rain {d['rain_mm']:g} mm, {s}",
                      f"• {d['date']}: {d['min_c']:g}–{d['max_c']:g}°C, ಮಳೆ {d['rain_mm']:g} ಮಿ.ಮೀ, {s}",
                      f"• {d['date']}: {d['min_c']:g}–{d['max_c']:g}°C, बारिश {d['rain_mm']:g} मिमी, {s}"))
    return "\n".join(out)


def _render_help(persona: str, lang: str) -> str:
    if persona == "farmer":
        return _t(lang,
                  "I can tell you today's price for your crop, whether to hold or sell, which mandi pays best, last year's price, arrivals, and the weather. I can also search the web for schemes, MSP, fertiliser and pests. Try: \"What is tomato worth in Kolar?\"",
                  "ನಿಮ್ಮ ಬೆಳೆಯ ಇಂದಿನ ಬೆಲೆ, ಹಿಡಿದಿಡಬೇಕೇ ಮಾರಬೇಕೇ, ಯಾವ ಮಂಡಿಯಲ್ಲಿ ಹೆಚ್ಚು ಬೆಲೆ, ಕಳೆದ ವರ್ಷದ ಬೆಲೆ, ಆವಕ ಮತ್ತು ಹವಾಮಾನ ಹೇಳಬಲ್ಲೆ. ಯೋಜನೆಗಳು, ಬೆಂಬಲ ಬೆಲೆ, ಗೊಬ್ಬರ, ಕೀಟಗಳ ಬಗ್ಗೆ ವೆಬ್‌ನಲ್ಲೂ ಹುಡುಕಬಲ್ಲೆ. ಕೇಳಿ: \"ಕೋಲಾರದಲ್ಲಿ ಟೊಮೇಟೊ ಬೆಲೆ ಎಷ್ಟು?\"",
                  "मैं आपकी फसल का आज का भाव, रोकें या बेचें, कौन-सी मंडी सबसे अच्छी, पिछले साल का भाव, आवक और मौसम बता सकता हूँ। योजनाओं, एमएसपी, खाद और कीटों के लिए वेब पर भी खोज सकता हूँ। पूछिए: \"कोलार में टमाटर का भाव क्या है?\"")
    return _t(lang,
              "I can run the desk tools: mandi spreads, gap arbitrage, volatility regime, historical analogs, scenarios, forward price, and the decision brief, and search the web for anything else. Try: \"Is the tomato spread at Kolar worth the trip?\"",
              "ನಾನು ಡೆಸ್ಕ್ ಸಾಧನಗಳನ್ನು ಬಳಸಬಲ್ಲೆ: ಮಂಡಿ ಅಂತರ, ಜಿಲ್ಲೆಗಳ ಅಂತರ ಅವಕಾಶ, ಅಸ್ಥಿರತೆ ಸ್ಥಿತಿ, ಐತಿಹಾಸಿಕ ಹೋಲಿಕೆ, ಸನ್ನಿವೇಶಗಳು, ಮುಂದಿನ ಬೆಲೆ, ನಿರ್ಧಾರ ಸಾರಾಂಶ; ಬೇರೆ ವಿಷಯಗಳಿಗೆ ವೆಬ್‌ನಲ್ಲಿ ಹುಡುಕುತ್ತೇನೆ.",
              "मैं डेस्क के टूल चला सकता हूँ: मंडी स्प्रेड, ज़िलों का अंतर, अस्थिरता की स्थिति, ऐतिहासिक समानताएँ, परिदृश्य, फ़ॉरवर्ड भाव और निर्णय संक्षेप; बाकी के लिए वेब पर खोजता हूँ।")


def _render_spread(r: Dict[str, Any], crop: str, lang: str) -> str:
    if r.get("status") != "OK":
        return _unavailable(lang)
    head = _t(lang, f"{crop}: {r['mandis_compared']} mandis compared as of {r['as_of']}; {r['survivors']} spreads survive the trip and {r['vanishing']} do not.",
              f"{crop}: {r['as_of']} ರಂತೆ {r['mandis_compared']} ಮಂಡಿಗಳ ಹೋಲಿಕೆ; {r['survivors']} ಅಂತರಗಳು ಪ್ರಯಾಣದ ನಂತರವೂ ಉಳಿಯುತ್ತವೆ, {r['vanishing']} ಇಲ್ಲ.",
              f"{crop}: {r['as_of']} तक {r['mandis_compared']} मंडियों की तुलना; {r['survivors']} स्प्रेड सफ़र के बाद बचते हैं, {r['vanishing']} नहीं।")
    ops = r.get("opportunities") or []
    if not ops:
        return head
    o = ops[0]
    line = _t(lang, f"Top route: {o['buy_mandi_name']} → {o['sell_mandi_name']}: today {sinr(o['today_net_per_quintal'])}/q, expected on arrival {sinr(o['expected_net_on_arrival_per_quintal'])}/q ({o['distance_km']:g} km, {o['vehicle']}).",
              f"ಅಗ್ರ ಮಾರ್ಗ: {o['buy_mandi_name']} → {o['sell_mandi_name']}: ಇಂದು {sinr(o['today_net_per_quintal'])}/ಕ್ವಿಂ, ತಲುಪಿದಾಗ ನಿರೀಕ್ಷೆ {sinr(o['expected_net_on_arrival_per_quintal'])}/ಕ್ವಿಂ ({o['distance_km']:g} ಕಿ.ಮೀ).",
              f"शीर्ष रूट: {o['buy_mandi_name']} → {o['sell_mandi_name']}: आज {sinr(o['today_net_per_quintal'])}/क्विं, पहुँचने पर अपेक्षित {sinr(o['expected_net_on_arrival_per_quintal'])}/क्विं ({o['distance_km']:g} किमी)।")
    return head + "\n" + line


def _render_gap(r: Dict[str, Any], crop: str, lang: str) -> str:
    pairs = r.get("pairs") or []
    if r.get("status") != "OK" or not pairs:
        return _unavailable(lang)
    p = pairs[0]
    a, b = place_name(p["cheaper_district"], lang), place_name(p["dearer_district"], lang)
    verdict = _t(lang, "worth hauling" if p["worth_hauling"] else "not worth hauling", "ಸಾಗಿಸುವುದು ಲಾಭಕರ" if p["worth_hauling"] else "ಸಾಗಿಸುವುದು ಲಾಭಕರವಲ್ಲ", "ढोना फ़ायदेमंद" if p["worth_hauling"] else "ढोना फ़ायदेमंद नहीं")
    return _t(lang, f"{crop}: {a} is {p['current_gap_pct']:.1f}% cheaper than {b} now; projected on arrival {p['projected_gap_pct_on_arrival']:.1f}% (half-life {p['half_life_weeks']:.1f} weeks). After transport ({p['transport_pct']:.1f}%) the margin is {p['net_gross_margin_pct']:.1f}%: {verdict}.",
              f"{crop}: {a} ಈಗ {b}ಗಿಂತ {p['current_gap_pct']:.1f}% ಅಗ್ಗ; ತಲುಪಿದಾಗ {p['projected_gap_pct_on_arrival']:.1f}% (ಅರ್ಧಾಯುಷ್ಯ {p['half_life_weeks']:.1f} ವಾರ). ಸಾಗಣೆ ({p['transport_pct']:.1f}%) ನಂತರ ಲಾಭಾಂಶ {p['net_gross_margin_pct']:.1f}%: {verdict}.",
              f"{crop}: {a} अभी {b} से {p['current_gap_pct']:.1f}% सस्ता है; पहुँचने पर {p['projected_gap_pct_on_arrival']:.1f}% (अर्ध-आयु {p['half_life_weeks']:.1f} सप्ताह)। ढुलाई ({p['transport_pct']:.1f}%) के बाद मार्जिन {p['net_gross_margin_pct']:.1f}%: {verdict}।")


_REG = {"CALM": ("calm", "ಶಾಂತ", "शांत"), "NORMAL": ("normal", "ಸಾಮಾನ್ಯ", "सामान्य"), "TURBULENT": ("turbulent", "ಅಸ್ಥಿರ", "अस्थिर")}


def _render_vol(r: Dict[str, Any], crop: str, lang: str) -> str:
    if r.get("status") != "OK":
        return _unavailable(lang)
    reg = r["current_regime"]
    name = _REG.get(reg, (reg, reg, reg))[{"en": 0, "kn": 1, "hi": 2}[lang]]
    w = (r.get("windows") or {}).get("20") or {}
    share = r.get("regime_share", {})
    line = _t(lang, f"{crop} at {place_name(r['mandi_id'], lang)} is in a {name} volatility regime as of {r['as_of']}.",
              f"{place_name(r['mandi_id'], lang)}ದಲ್ಲಿ {crop} {r['as_of']} ರಂತೆ {name} ಏರಿಳಿತ ಸ್ಥಿತಿಯಲ್ಲಿದೆ.",
              f"{place_name(r['mandi_id'], lang)} में {crop} {r['as_of']} तक {name} अस्थिरता की स्थिति में है।")
    if w:
        line += "\n" + _t(lang, f"20-print volatility is {w['current_daily_pct']:.1f}% a day, at the {w['percentile']:.0f}th percentile of its own history.",
                          f"20 ದಾಖಲೆಗಳ ಏರಿಳಿತ ದಿನಕ್ಕೆ {w['current_daily_pct']:.1f}%, ತನ್ನದೇ ಇತಿಹಾಸದ {w['percentile']:.0f}ನೇ ಶತಮಾನದಲ್ಲಿ.",
                          f"20 प्रिंट की अस्थिरता रोज़ {w['current_daily_pct']:.1f}% है, अपने इतिहास के {w['percentile']:.0f}वें पर्सेंटाइल पर।")
    if share:
        line += "\n" + _t(lang, f"Historically: calm {share.get('CALM', 0) * 100:.0f}%, normal {share.get('NORMAL', 0) * 100:.0f}%, turbulent {share.get('TURBULENT', 0) * 100:.0f}% of the time.",
                          f"ಇತಿಹಾಸದಲ್ಲಿ: ಶಾಂತ {share.get('CALM', 0) * 100:.0f}%, ಸಾಮಾನ್ಯ {share.get('NORMAL', 0) * 100:.0f}%, ಅಸ್ಥಿರ {share.get('TURBULENT', 0) * 100:.0f}%.",
                          f"इतिहास में: शांत {share.get('CALM', 0) * 100:.0f}%, सामान्य {share.get('NORMAL', 0) * 100:.0f}%, अस्थिर {share.get('TURBULENT', 0) * 100:.0f}%।")
    return line


def _render_analog(r: Dict[str, Any], crop: str, lang: str) -> str:
    o, base = r.get("outcome"), r.get("baseline")
    if r.get("status") != "OK" or not o:
        return _unavailable(lang)
    return _t(lang, f"{o['n']} past periods looked like today's {crop} path. {o['share_up'] * 100:.0f}% were higher {r['horizon_days']} days later (median {o['median_pct']:+.1f}%, 10th–90th percentile {o['p10_pct']:+.1f}% to {o['p90_pct']:+.1f}%), against a baseline of {base['share_up'] * 100:.0f}% up. This is precedent, not a forecast.",
              f"ಇಂದಿನ {crop} ಚಲನೆಯನ್ನು ಹೋಲುವ {o['n']} ಹಿಂದಿನ ಅವಧಿಗಳು ಸಿಕ್ಕಿವೆ. {r['horizon_days']} ದಿನಗಳ ನಂತರ {o['share_up'] * 100:.0f}% ಬಾರಿ ಬೆಲೆ ಹೆಚ್ಚಿತ್ತು (ಮಧ್ಯಾಂಕ {o['median_pct']:+.1f}%, {o['p10_pct']:+.1f}% ರಿಂದ {o['p90_pct']:+.1f}%); ಸಾಮಾನ್ಯವಾಗಿ {base['share_up'] * 100:.0f}%. ಇದು ಹಿಂದಿನ ಉದಾಹರಣೆ, ಮುನ್ಸೂಚನೆಯಲ್ಲ.",
              f"आज के {crop} के रुझान जैसे {o['n']} पिछले दौर मिले। {r['horizon_days']} दिन बाद {o['share_up'] * 100:.0f}% बार भाव ऊपर था (माध्यिका {o['median_pct']:+.1f}%, {o['p10_pct']:+.1f}% से {o['p90_pct']:+.1f}%); सामान्यतः {base['share_up'] * 100:.0f}%। यह पूर्व-उदाहरण है, पूर्वानुमान नहीं।")


def _render_scenarios(r: Dict[str, Any], crop: str, lang: str) -> str:
    sc = r.get("scenarios") or []
    if r.get("status") != "OK" or not sc:
        return _unavailable(lang)
    active = [s for s in sc if s.get("condition_active_now") and s.get("outcome")]
    if not active:
        return _t(lang, f"No scenario condition is active for {crop} today, so there is no matching precedent to cite.",
                  f"{crop}ಗೆ ಇಂದು ಯಾವ ಸನ್ನಿವೇಶದ ಸ್ಥಿತಿಯೂ ಸಕ್ರಿಯವಾಗಿಲ್ಲ, ಹಾಗಾಗಿ ಉಲ್ಲೇಖಿಸಲು ಹೊಂದುವ ಹಿಂದಿನ ಉದಾಹರಣೆ ಇಲ್ಲ.",
                  f"{crop} के लिए आज कोई परिदृश्य सक्रिय नहीं है, इसलिए हवाला देने लायक कोई पूर्व-उदाहरण नहीं।")
    out = [_t(lang, f"Active conditions for {crop} and what followed historically:", f"{crop}ಗೆ ಸಕ್ರಿಯ ಸ್ಥಿತಿಗಳು ಮತ್ತು ಹಿಂದೆ ಏನಾಯಿತು:", f"{crop} की सक्रिय स्थितियाँ और इतिहास में आगे क्या हुआ:")]
    for s in active:
        o = s["outcome"]
        label = (translate(s['label'], lang) if lang != 'en' else None) or s['label']
        out.append(_t(lang, f"• {s['label']}: median {o['median_pct']:+.1f}%, {o['share_down'] * 100:.0f}% of episodes fell ({s['episodes']} episodes).",
                      f"• {label}: ಮಧ್ಯಾಂಕ {o['median_pct']:+.1f}%, {o['share_down'] * 100:.0f}% ಬಾರಿ ಬೆಲೆ ಇಳಿಯಿತು ({s['episodes']} ಘಟನೆಗಳು).",
                      f"• {label}: माध्यिका {o['median_pct']:+.1f}%, {o['share_down'] * 100:.0f}% बार भाव गिरा ({s['episodes']} घटनाएँ)।"))
    return "\n".join(out)


def _render_forward(r: Dict[str, Any], crop: str, lang: str) -> str:
    if r.get("status") == "UNSUITABLE":
        m = re.search(r"(\d+) day", str(r.get("reason", "")))
        days = m.group(1) if m else "a few"
        return _t(lang, r.get("reason", ""),
                  f"{crop} ಸಾಮಾನ್ಯ ಸಂಗ್ರಹದಲ್ಲಿ ಸುಮಾರು {days} ದಿನ ಮಾತ್ರ ಉಳಿಯುತ್ತದೆ; ಇಷ್ಟು ದೀರ್ಘ ಫಾರ್ವರ್ಡ್ ಒಪ್ಪಂದದಲ್ಲಿ ಬೆಳೆ ಹಾಳಾಗಿರುತ್ತದೆ. ಕಡಿಮೆ ಅವಧಿ ಆರಿಸಿ.",
                  f"{crop} सामान्य भंडारण में लगभग {days} दिन ही टिकता है; इतने लंबे फ़ॉरवर्ड सौदे में फसल खराब हो चुकी होगी। छोटी अवधि चुनें।")
    if r.get("status") != "OK":
        return _unavailable(lang)
    lo, hi = r["delivery_price_range_90"]
    h, exp = r["horizon_days"], r["expected_price_at_delivery"]
    lines = [_t(lang, f"{crop} in {r['horizon_days']} days: expected delivery price about {inr(exp)} per quintal (90% range {inr(lo)} to {inr(hi)}), from the latest price of {inr(r['base_price'])} on {r['base_date']}.",
                f"{h} ದಿನಗಳಲ್ಲಿ {crop}: ನಿರೀಕ್ಷಿತ ವಿತರಣಾ ಬೆಲೆ ಕ್ವಿಂಟಾಲ್‌ಗೆ ಸುಮಾರು {inr(exp)} (90% ಶ್ರೇಣಿ {inr(lo)} ರಿಂದ {inr(hi)}); {r['base_date']} ರ ಬೆಲೆ {inr(r['base_price'])} ಆಧರಿಸಿ.",
                f"{h} दिन में {crop}: अपेक्षित डिलीवरी भाव लगभग {inr(exp)} प्रति क्विंटल (90% दायरा {inr(lo)} से {inr(hi)}), {r['base_date']} के भाव {inr(r['base_price'])} के आधार पर।")]
    if r.get("deal_possible") is False:
        lines.append(_t(lang, f"No deal overlap: the farmer needs at least {inr(r['farmer_floor'])} to beat selling today, but a risk-adjusted trader ceiling is {inr(r['trader_ceiling'])}. Spoilage over the wait is {r['spoilage_over_horizon_pct']:.0f}%.",
                        f"ಒಪ್ಪಂದಕ್ಕೆ ಹೊಂದಾಣಿಕೆ ಇಲ್ಲ: ಇಂದು ಮಾರುವುದನ್ನು ಮೀರಲು ರೈತನಿಗೆ ಕನಿಷ್ಠ {inr(r['farmer_floor'])} ಬೇಕು, ಆದರೆ ವ್ಯಾಪಾರಿಯ ಅಪಾಯ-ಹೊಂದಿಸಿದ ಮಿತಿ {inr(r['trader_ceiling'])}. ಕಾಯುವಾಗ ಹಾಳಾಗುವಿಕೆ {r['spoilage_over_horizon_pct']:.0f}%.",
                        f"सौदे का मेल नहीं: आज बेचने से बेहतर होने के लिए किसान को कम से कम {inr(r['farmer_floor'])} चाहिए, पर व्यापारी की जोखिम-समायोजित सीमा {inr(r['trader_ceiling'])} है। इंतज़ार में खराबी {r['spoilage_over_horizon_pct']:.0f}%।"))
    elif r.get("deal_possible"):
        lines.append(_t(lang, f"A deal is possible between {inr(r['farmer_floor'])} (farmer floor) and {inr(r['trader_ceiling'])} (trader ceiling).",
                        f"{inr(r['farmer_floor'])} (ರೈತನ ಕನಿಷ್ಠ) ಮತ್ತು {inr(r['trader_ceiling'])} (ವ್ಯಾಪಾರಿಯ ಗರಿಷ್ಠ) ನಡುವೆ ಒಪ್ಪಂದ ಸಾಧ್ಯ.",
                        f"{inr(r['farmer_floor'])} (किसान की न्यूनतम) और {inr(r['trader_ceiling'])} (व्यापारी की अधिकतम) के बीच सौदा संभव है।"))
    if r.get("price_age_days", 0) > 14:
        lines.append(_t(lang, f"Note: the base price is {r['price_age_days']} days old, so treat this as indicative.",
                        f"ಸೂಚನೆ: ಆಧಾರ ಬೆಲೆ {r['price_age_days']} ದಿನ ಹಳೆಯದು, ಆದ್ದರಿಂದ ಇದನ್ನು ಸೂಚಕವಾಗಿ ಮಾತ್ರ ಬಳಸಿ.",
                        f"ध्यान दें: आधार भाव {r['price_age_days']} दिन पुराना है, इसलिए इसे संकेत भर मानें।"))
    return "\n".join(lines)


def _render_brief(r: Dict[str, Any], crop: str, lang: str) -> str:
    if r.get("status") == "UNAVAILABLE" or "action" not in r:
        return _unavailable(lang)
    headline = (translate(r['headline'], lang) if lang != 'en' else None) or r['headline']
    return _t(lang, f"Decision brief for {crop}: {_action(r['action'], lang)} (confidence {_conf(r['confidence'], lang)}). {r['headline']}",
              f"{crop} ನಿರ್ಧಾರ ಸಾರಾಂಶ: {_action(r['action'], lang)} (ವಿಶ್ವಾಸ: {_conf(r['confidence'], lang)}). {headline}",
              f"{crop} का निर्णय संक्षेप: {_action(r['action'], lang)} (भरोसा: {_conf(r['confidence'], lang)})। {headline}")


def _render_web(res: Dict[str, Any], lang: str) -> Fallback:
    hits = [h for h in res.get("results", []) if h.get("url")][:3]
    if not hits:
        return Fallback(_t(lang, "The mandi records don't cover this, and I couldn't reach the web just now. Please try again in a moment.",
                           "ಇದು ಮಂಡಿ ದಾಖಲೆಗಳಲ್ಲಿ ಇಲ್ಲ, ಮತ್ತು ಈಗ ವೆಬ್ ತಲುಪಲು ಆಗಲಿಲ್ಲ. ಸ್ವಲ್ಪ ಸಮಯದ ನಂತರ ಪ್ರಯತ್ನಿಸಿ.",
                           "यह मंडी रिकॉर्ड में नहीं है, और अभी वेब तक नहीं पहुँच सका। थोड़ी देर बाद कोशिश करें।"), "web")
    body, translated_all = [], True
    for h in hits:
        snippet = re.sub(r"\s+", " ", h.get("snippet", "")).strip()[:200]
        line = f"{h['title']}: {snippet}" if snippet else h["title"]
        if lang != "en":
            native = translate(line, lang)
            if native:
                line = native
            else:
                translated_all = False
        body.append(f"• {line}")
    lead = _t(lang, "This isn't in the mandi records, so I searched the web. The top results say:",
              "ಇದು ಮಂಡಿ ದಾಖಲೆಗಳಲ್ಲಿ ಇಲ್ಲ, ಹಾಗಾಗಿ ವೆಬ್‌ನಲ್ಲಿ ಹುಡುಕಿದೆ. ಮೊದಲ ಫಲಿತಾಂಶಗಳು ಹೀಗೆ ಹೇಳುತ್ತವೆ" + (":" if translated_all else " (ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ, ಅನುವಾದ ಸಾಧ್ಯವಾಗಲಿಲ್ಲ):"),
              "यह मंडी रिकॉर्ड में नहीं है, इसलिए वेब पर खोजा। शीर्ष नतीजे यह कहते हैं" + (":" if translated_all else " (अंग्रेज़ी में, अनुवाद नहीं हो सका):"))
    return Fallback(lead + "\n" + "\n".join(body), "web", [{"title": h["title"], "url": h["url"]} for h in hits])


# ── entry point ─────────────────────────────────────────────────────────────

def answer(persona: str, message: str, lang: str, ent: Entities, run: Run, default_district: str = "kolar",
           current: Optional[Entities] = None) -> Fallback:
    res = _answer(persona, message, lang, ent, run, default_district, current)
    if lang == "en":  # crop names are lower-case inside sentences; capitalise each line
        lines = res.text.split("\n")
        res.text = "\n".join((ln[:1].upper() + ln[1:]) if ln[:1].isalpha() else ln for ln in lines)
    return res


def _answer(persona: str, message: str, lang: str, ent: Entities, run: Run, default_district: str,
            current: Optional[Entities]) -> Fallback:
    intent = route(persona, message, ent, current)
    if intent == "help":
        return Fallback(_render_help(persona, lang), "help")
    if intent == "web":
        return _render_web(run("web_search", {"query": message}), lang)
    if intent == "weather":
        place = place_name(ent.mandi_id or ent.district or default_district, "en").split(" (")[0]
        return Fallback(_render_weather(run("get_weather", {"place": place, "days": 3}), lang, place_name(ent.mandi_id or ent.district or default_district, lang).split(" (")[0]), "weather", [{"title": "Open-Meteo", "url": "https://open-meteo.com"}])
    if intent == "accuracy":
        return Fallback(_render_accuracy(run("get_accuracy", {}), lang), "accuracy")

    if intent == "clarify":
        ent = Entities(**{**ent.as_dict(), "crop": None})
    assumed = ent.district is None and ent.mandi_id is None
    district = ent.district or default_district
    mandi = ent.mandi_id or f"{district}_apmc"
    if not ent.crop:
        ask = _t(lang, "Which crop do you mean? I have tomato, onion, potato, ginger, garlic and dry chillies.",
                 "ಯಾವ ಬೆಳೆ ಬಗ್ಗೆ ಕೇಳುತ್ತಿದ್ದೀರಿ? ನನ್ನ ಬಳಿ ಟೊಮೇಟೊ, ಈರುಳ್ಳಿ, ಆಲೂಗಡ್ಡೆ, ಶುಂಠಿ, ಬೆಳ್ಳುಳ್ಳಿ, ಒಣ ಮೆಣಸಿನಕಾಯಿ ಮಾಹಿತಿ ಇದೆ.",
                 "आप किस फसल की बात कर रहे हैं? मेरे पास टमाटर, प्याज़, आलू, अदरक, लहसुन और सूखी मिर्च की जानकारी है।")
        return Fallback(ask, "clarify")
    crop, cname = ent.crop, crop_name(ent.crop, lang)
    qty = ent.quantity_quintals or 10.0

    if intent == "price":
        return _price_answer(run, crop, district, ent, lang, assumed)
    if intent == "sell":
        t = normalise_digits(message).lower()
        if _has(t, _WEAK_SELL):
            return Fallback(_render_plan(run("get_sell_plan", {"crop": crop, "mandi_id": mandi, "quantity_quintals": qty}), cname, qty, lang) + _assumed(lang, place_name(mandi, lang), assumed), "sell_plan")
        return Fallback(_render_hold(run("get_hold_or_sell", {"crop": crop, "mandi_id": mandi, "quantity_quintals": qty}), cname, qty, lang) + _assumed(lang, place_name(mandi, lang), assumed), "hold_or_sell")
    if intent == "where":
        return Fallback(_render_where(run("get_where_to_sell", {"crop": crop, "mandi_id": mandi, "quantity_quintals": qty}), cname, lang) + _assumed(lang, place_name(mandi, lang), assumed), "where")
    if intent == "seasonal":
        return Fallback(_render_seasonal(run("get_seasonal_memory", {"crop": crop, "mandi_id": mandi}), cname, lang), "seasonal")
    if intent == "supply":
        return Fallback(_render_supply(run("get_supply_signal", {"crop": crop, "mandi_id": mandi}), cname, lang), "supply")
    if intent == "spread":
        return Fallback(_render_spread(run("scan_spreads", {"crop": crop, "quantity_quintals": qty}), cname, lang), "spreads")
    if intent == "gap":
        return Fallback(_render_gap(run("gap_arbitrage", {"crop": crop, "quantity_quintals": qty}), cname, lang), "gap")
    if intent == "vol":
        return Fallback(_render_vol(run("get_volatility", {"crop": crop, "mandi_id": mandi}), cname, lang), "volatility")
    if intent == "analog":
        return Fallback(_render_analog(run("get_analogs", {"crop": crop, "mandi_id": mandi, "horizon_days": ent.horizon_days or 7}), cname, lang), "analogs")
    if intent == "scenario":
        return Fallback(_render_scenarios(run("run_scenarios", {"crop": crop, "mandi_id": mandi, "horizon_days": ent.horizon_days or 5}), cname, lang), "scenarios")
    if intent == "forward":
        return Fallback(_render_forward(run("get_forward_price", {"crop": crop, "mandi_id": mandi, "horizon_days": ent.horizon_days or 3, "quantity_quintals": qty}), cname, lang), "forward")
    if intent == "brief":
        return Fallback(_render_brief(run("get_decision_brief", {"crop": crop, "mandi_id": mandi}), cname, lang), "brief")
    if intent == "transmission":
        res = run("get_transmission_matrix", {})
        return Fallback(_unavailable(lang) if res.get("error") else str(res)[:600], "transmission")
    return _price_answer(run, crop, district, ent, lang, assumed)


def _price_answer(run: Run, crop: str, district: str, ent: Entities, lang: str, assumed: bool) -> Fallback:
    b = run("get_price_board", {"crop": crop, "district": district})
    if b.get("status") != "OK":
        return Fallback(_unavailable(lang), "price")
    return Fallback(_render_price(b, ent, lang, assumed), "price")
