"""
The daily market digest a farmer receives.

Built only from data already ingested (the market panel and the market-choice engines), so it never pretends
to know today's price: every figure carries the date it was reported, and the message says how old the data
is. Advice on where to sell is given only for crops whose engine has strong back-test evidence; potato
(limited evidence) and garlic (no choice between markets) get prices only.
"""

from __future__ import annotations

import html
from datetime import date
from functools import lru_cache
from typing import Any, Dict, List, Optional

import pandas as pd

from mandisense_ai.farmer import registry, world

CROPS = ("tomato", "onion", "potato", "ginger", "garlic")
LANGS = ("en", "kn", "hi")
SILENT_WARN = 0.6          # warn when a mandi reported on fewer than 40% of this weekday in the last year
OLD_PRICE_DAYS = 14        # a last report older than this is labelled old

CROP_NAMES = {
    "en": {"tomato": "Tomato", "onion": "Onion", "potato": "Potato", "ginger": "Ginger", "garlic": "Garlic"},
    "kn": {"tomato": "ಟೊಮೆಟೊ", "onion": "ಈರುಳ್ಳಿ", "potato": "ಆಲೂಗಡ್ಡೆ", "ginger": "ಶುಂಠಿ", "garlic": "ಬೆಳ್ಳುಳ್ಳಿ"},
    "hi": {"tomato": "टमाटर", "onion": "प्याज", "potato": "आलू", "ginger": "अदरक", "garlic": "लहसुन"},
}
WEEKDAYS = {
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
    "kn": ["ಸೋಮವಾರ", "ಮಂಗಳವಾರ", "ಬುಧವಾರ", "ಗುರುವಾರ", "ಶುಕ್ರವಾರ", "ಶನಿವಾರ", "ಭಾನುವಾರ"],
    "hi": ["सोमवार", "मंगलवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार"],
}
T = {
    "title": {"en": "MandiSense market update", "kn": "ಮಂಡಿಸೆನ್ಸ್ ಮಾರುಕಟ್ಟೆ ಮಾಹಿತಿ", "hi": "मंडीसेंस बाज़ार जानकारी"},
    "for": {"en": "for", "kn": "ಪ್ರದೇಶ:", "hi": "क्षेत्र:"},
    "prices_upto": {"en": "Prices reported up to {d}", "kn": "{d} ವರೆಗೆ ವರದಿಯಾದ ಬೆಲೆಗಳು", "hi": "{d} तक दर्ज भाव"},
    "stale": {"en": "Data is {n} days old; prices may have moved since.", "kn": "ಮಾಹಿತಿ {n} ದಿನ ಹಳೆಯದು; ಬೆಲೆ ಬದಲಾಗಿರಬಹುದು.",
              "hi": "जानकारी {n} दिन पुरानी है; भाव बदल चुके हो सकते हैं।"},
    "at": {"en": "at", "kn": "", "hi": "में"},
    "per_q": {"en": "/quintal", "kn": "/ಕ್ವಿಂಟಾಲ್", "hi": "/क्विंटल"},
    "vs_week": {"en": "vs 7-day average", "kn": "7 ದಿನದ ಸರಾಸರಿಗೆ ಹೋಲಿಸಿ", "hi": "7 दिन के औसत से"},
    "old": {"en": "old", "kn": "ಹಳೆಯದು", "hi": "पुराना"},
    "no_report": {"en": "no price reported recently", "kn": "ಇತ್ತೀಚೆಗೆ ಬೆಲೆ ವರದಿಯಾಗಿಲ್ಲ", "hi": "हाल में भाव दर्ज नहीं"},
    "best": {"en": "Best place to sell", "kn": "ಮಾರಾಟಕ್ಕೆ ಉತ್ತಮ ಸ್ಥಳ", "hi": "बेचने की सबसे अच्छी जगह"},
    "sell_now": {"en": "sell on the next market day", "kn": "ಮುಂದಿನ ಮಾರುಕಟ್ಟೆ ದಿನವೇ ಮಾರಿ", "hi": "अगले बाज़ार दिन बेचें"},
    "hold": {"en": "wait {k} day(s), then sell", "kn": "{k} ದಿನ ಕಾಯ್ದು ನಂತರ ಮಾರಿ", "hi": "{k} दिन रुककर बेचें"},
    "farm_gate": {"en": "Sell at the farm gate", "kn": "ಜಮೀನಿನಲ್ಲೇ ಮಾರಾಟ ಮಾಡಿ", "hi": "खेत पर ही बेचें"},
    "net": {"en": "about ₹{x}{u} after transport and fees", "kn": "ಸಾಗಣೆ ಮತ್ತು ಶುಲ್ಕದ ನಂತರ ಸುಮಾರು ₹{x}{u}",
            "hi": "ढुलाई और शुल्क के बाद लगभग ₹{x}{u}"},
    "floor": {"en": "at least ₹{x} on 9 days in 10", "kn": "10ರಲ್ಲಿ 9 ದಿನ ಕನಿಷ್ಠ ₹{x}", "hi": "10 में 9 दिन कम से कम ₹{x}"},
    "gain": {"en": "₹{x} more than the nearest mandi", "kn": "ಹತ್ತಿರದ ಮಂಡಿಗಿಂತ ₹{x} ಹೆಚ್ಚು", "hi": "नज़दीकी मंडी से ₹{x} अधिक"},
    "price_only": {"en": "Prices only: the evidence is not strong enough to advise where to sell.",
                   "kn": "ಕೇವಲ ಬೆಲೆಗಳು: ಎಲ್ಲಿ ಮಾರಬೇಕೆಂದು ಸಲಹೆ ನೀಡಲು ಸಾಕ್ಷ್ಯ ಸಾಕಾಗುವುದಿಲ್ಲ.",
                   "hi": "केवल भाव: कहाँ बेचें, यह सलाह देने लायक प्रमाण पर्याप्त नहीं।"},
    "warn_silent": {"en": "{m} reported no price on {p}% of {w}s last year.",
                    "kn": "ಕಳೆದ ವರ್ಷ {w}ಗಳಲ್ಲಿ {p}% ದಿನ {m} ಬೆಲೆ ವರದಿ ಮಾಡಿಲ್ಲ.",
                    "hi": "पिछले साल {p}% {w} को {m} में भाव दर्ज नहीं हुआ।"},
    "footer": {"en": "Advice, not a promise. /today for an update, /stop to unsubscribe.",
               "kn": "ಇದು ಸಲಹೆ, ಖಾತರಿ ಅಲ್ಲ. ಹೊಸ ಮಾಹಿತಿಗೆ /today, ನಿಲ್ಲಿಸಲು /stop.",
               "hi": "यह सलाह है, गारंटी नहीं। ताज़ा जानकारी /today, बंद करने के लिए /stop."},
}


def t(key: str, lang: str, **kw) -> str:
    s = T[key].get(lang) or T[key]["en"]
    return s.format(**kw) if kw else s


def _mandi_name(mid: str, lang: str) -> str:
    m = registry.MANDIS.get(mid)
    if not m:
        return mid
    return {"kn": m.name_kn, "hi": m.name_hi}.get(lang) or m.name


def _rs(x: float) -> str:
    return f"{x:,.0f}"


@lru_cache(maxsize=1)
def panel() -> pd.DataFrame:
    p = pd.read_parquet(world.MARKET_PANEL)
    p["date"] = pd.to_datetime(p["date"])
    return p


def latest_price(crop: str, mandi_id: str) -> Optional[Dict[str, Any]]:
    """Last reported modal price, its date and the change against the mean of the 7 reports before it."""
    g = panel()
    g = g[(g["crop"] == crop) & (g["mandi_id"] == mandi_id)].sort_values("date")
    if g.empty:
        return None
    last = g.iloc[-1]
    prev = g.iloc[-8:-1]["price"]
    change = (last["price"] / prev.mean() - 1) * 100 if len(prev) >= 3 and prev.mean() > 0 else None
    return {"price": float(last["price"]), "date": last["date"].date(), "change_pct": change}


def weekday_silence(crop: str, mandi_id: str, weekday: int, days: int = 365) -> Optional[float]:
    """Share of the given weekday in the last `days` on which the mandi reported no price for the crop."""
    p = panel()
    end = p["date"].max()
    cal = pd.date_range(end - pd.Timedelta(days=days), end)
    cal = cal[cal.dayofweek == weekday]
    if len(cal) < 10:
        return None
    rep = set(p[(p["crop"] == crop) & (p["mandi_id"] == mandi_id)]["date"])
    if not rep:
        return None
    return 1 - sum(d in rep for d in cal) / len(cal)


def data_as_of() -> date:
    return panel()["date"].max().date()


@lru_cache(maxsize=64)
def _recommend(crop: str, district: str) -> Dict[str, Any]:
    from mandisense_ai.market_choice import service

    origin = service.resolve_origin(district, None, None, None)
    if origin is None:
        return {"status": "UNAVAILABLE"}
    return service.recommend(crop, origin, 1.0)


def crop_block(crop: str, district: str, lang: str) -> List[str]:
    """Lines for one crop: home-mandi price with date, then advice where the evidence allows it."""
    d = registry.DISTRICTS[district]
    lines = [f"<b>{html.escape(CROP_NAMES[lang][crop])}</b>"]
    # the district's mandi with the most recent report for this crop (the anchor mandi wins ties)
    cands = [d.anchor_mandi] + [m.id for m in registry.mandis_in(district) if m.id != d.anchor_mandi]
    found = [(mid, latest_price(crop, mid)) for mid in cands]
    found = [(mid, lp) for mid, lp in found if lp]
    if found:
        home, lp = max(found, key=lambda x: x[1]["date"])
        old = (data_as_of() - lp["date"]).days > OLD_PRICE_DAYS
        ch = f" ({lp['change_pct']:+.0f}% {t('vs_week', lang)})" if lp["change_pct"] is not None and not old else ""
        tag = f" ⚠️ {t('old', lang)}" if old else ""
        lines.append(f"• {html.escape(_mandi_name(home, lang))}: ₹{_rs(lp['price'])}{t('per_q', lang)} "
                     f"[{lp['date'].strftime('%d-%b')}{tag}]{ch}")
    else:
        lines.append(f"• {t('no_report', lang)}")

    rec = _recommend(crop, district)
    strong = rec.get("status") == "OK" and (rec.get("evidence") or {}).get("level") == "strong"
    if not strong:
        lines.append(f"<i>{t('price_only', lang)}</i>")
        return lines
    r = rec["recommended"]
    if r["kind"] == "farm_gate":
        lines.append(f"✅ {t('farm_gate', lang)}")
    else:
        when = t("sell_now", lang) if r["hold_days"] == 0 else t("hold", lang, k=r["hold_days"])
        lines.append(f"✅ {t('best', lang)}: <b>{html.escape(_mandi_name(r['mandi_id'], lang))}</b> ({r['distance_km']:.0f} km), {when}")
    lines.append(f"   {t('net', lang, x=_rs(r['expected_net_per_q']), u=t('per_q', lang))}; {t('floor', lang, x=_rs(r['floor_per_q']))}")
    g = (rec.get("gain") or {}).get("vs_nearest_per_q")
    if g and g > 0:
        lines.append(f"   {t('gain', lang, x=_rs(g))}")
    if r["kind"] == "mandi":
        wd = pd.Timestamp(r["sale_date"]).dayofweek
        s = weekday_silence(crop, r["mandi_id"], wd)
        if s is not None and s >= SILENT_WARN:
            lines.append("⚠️ " + t("warn_silent", lang, m=html.escape(_mandi_name(r["mandi_id"], lang)), p=round(100 * s), w=WEEKDAYS[lang][wd]))
    return lines


def build_digest(district: str, crops: List[str], lang: str = "en", today: Optional[date] = None) -> str:
    """The whole message (Telegram HTML)."""
    lang = lang if lang in LANGS else "en"
    today = today or date.today()
    d = registry.DISTRICTS[district]
    dname = {"kn": d.name_kn, "hi": d.name_hi}.get(lang) or d.name
    asof = data_as_of()
    out = [f"🌾 <b>{t('title', lang)}</b> {t('for', lang)} <b>{html.escape(dname)}</b>",
           f"🗓 {t('prices_upto', lang, d=asof.strftime('%d-%b-%Y'))}"]
    age = (today - asof).days
    if age > 2:
        out.append(f"⚠️ {t('stale', lang, n=age)}")
    for c in crops:
        if c in CROPS:
            out.append("")
            out.extend(crop_block(c, district, lang))
    out += ["", f"<i>{t('footer', lang)}</i>"]
    return "\n".join(out)
