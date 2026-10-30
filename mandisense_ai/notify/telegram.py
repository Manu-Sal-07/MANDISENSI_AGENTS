"""
Telegram delivery: a thin Bot API client and the farmer conversation.

    /start     choose language, district and crops with buttons, then receive today's digest
    /today     the digest now
    /settings  change language, district or crops
    /stop      unsubscribe (and /start again to come back)
    any text   e.g. "tomato kolar" or "ಈರುಳ್ಳಿ" returns the digest for what was named

Long polling, so the bot runs on a laptop without a public URL. The token is read from TELEGRAM_BOT_TOKEN
(the repository .env); it is never logged.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

import requests

from mandisense_ai.farmer import registry
from mandisense_ai.notify import digest, store
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)
API = "https://api.telegram.org/bot{token}/{method}"
DISTRICT_ORDER = ["kolar", "chikkaballapur", "bengaluru", "bengaluru_rural", "bengaluru_south"]

M = {
    "welcome": "🌾 <b>MandiSense</b>\nDaily mandi prices and where to sell, for farmers in the Bengaluru–Kolar belt.\n"
               "ಪ್ರತಿದಿನ ಮಂಡಿ ಬೆಲೆ ಮತ್ತು ಎಲ್ಲಿ ಮಾರಬೇಕು ಎಂಬ ಮಾಹಿತಿ.\nरोज़ मंडी भाव और कहाँ बेचें।\n\n"
               "Choose your language / ಭಾಷೆ ಆಯ್ಕೆಮಾಡಿ / भाषा चुनें:",
    "district": {"en": "Which district are you in?", "kn": "ನಿಮ್ಮ ಜಿಲ್ಲೆ ಯಾವುದು?", "hi": "आप किस ज़िले में हैं?"},
    "crops": {"en": "Which crops do you grow? Tap to select, then Done.", "kn": "ನೀವು ಯಾವ ಬೆಳೆ ಬೆಳೆಯುತ್ತೀರಿ? ಆಯ್ಕೆಮಾಡಿ, ನಂತರ ಮುಗಿಯಿತು.",
              "hi": "आप कौन-सी फसल उगाते हैं? चुनें, फिर पूरा।"},
    "done_btn": {"en": "Done ✅", "kn": "ಮುಗಿಯಿತು ✅", "hi": "पूरा ✅"},
    "pick_one": {"en": "Select at least one crop.", "kn": "ಕನಿಷ್ಠ ಒಂದು ಬೆಳೆ ಆಯ್ಕೆಮಾಡಿ.", "hi": "कम से कम एक फसल चुनें।"},
    "subscribed": {"en": "✅ Subscribed. You will get this update every morning at 7. Here is today's:",
                   "kn": "✅ ನೋಂದಣಿ ಆಯಿತು. ಪ್ರತಿದಿನ ಬೆಳಿಗ್ಗೆ 7ಕ್ಕೆ ಈ ಮಾಹಿತಿ ಬರುತ್ತದೆ. ಇಂದಿನದು:",
                   "hi": "✅ सदस्यता हो गई। हर सुबह 7 बजे यह जानकारी आएगी। आज की:"},
    "stopped": {"en": "You are unsubscribed. Send /start to subscribe again.", "kn": "ನೋಂದಣಿ ರದ್ದಾಗಿದೆ. ಮತ್ತೆ ಸೇರಲು /start ಕಳುಹಿಸಿ.",
                "hi": "सदस्यता बंद। फिर से जुड़ने के लिए /start भेजें।"},
    "help": {"en": "/today – today's update\n/settings – change language, district or crops\n/stop – unsubscribe\n"
                   "Or type a crop and place, e.g. <i>tomato kolar</i>.",
             "kn": "/today – ಇಂದಿನ ಮಾಹಿತಿ\n/settings – ಭಾಷೆ, ಜಿಲ್ಲೆ, ಬೆಳೆ ಬದಲಿಸಿ\n/stop – ನೋಂದಣಿ ರದ್ದು\nಅಥವಾ ಬೆಳೆ ಮತ್ತು ಸ್ಥಳ ಬರೆಯಿರಿ, ಉದಾ: <i>ಟೊಮೆಟೊ ಕೋಲಾರ</i>.",
             "hi": "/today – आज की जानकारी\n/settings – भाषा, ज़िला, फसल बदलें\n/stop – सदस्यता बंद\nया फसल और जगह लिखें, जैसे <i>टमाटर कोलार</i>।"},
    "not_understood": {"en": "I didn't recognise a crop or place.", "kn": "ಬೆಳೆ ಅಥವಾ ಸ್ಥಳ ಗುರುತಿಸಲಾಗಲಿಲ್ಲ.", "hi": "फसल या जगह पहचान नहीं पाया।"},
}


def m(key: str, lang: str) -> str:
    v = M[key]
    return v if isinstance(v, str) else (v.get(lang) or v["en"])


def load_token() -> str:
    tok = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not tok:
        from mandisense_ai.intelligence.providers import load_env

        load_env()
        tok = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not tok:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set (add it to the repository .env)")
    return tok


class Client:
    """Minimal Bot API client. `post` is replaceable in tests."""

    def __init__(self, token: Optional[str] = None, session: Optional[requests.Session] = None):
        self.token = token or load_token()
        self.session = session or requests.Session()

    def post(self, method: str, **params) -> Dict[str, Any]:
        data = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v) for k, v in params.items() if v is not None}
        r = self.session.post(API.format(token=self.token, method=method), data=data, timeout=params.get("timeout", 0) + 20)
        body = r.json()
        if not body.get("ok"):
            raise TelegramError(body.get("error_code"), body.get("description", ""))
        return body["result"]

    def send(self, chat_id: int, text: str, keyboard: Optional[List[List[Dict[str, str]]]] = None) -> Dict[str, Any]:
        markup = {"inline_keyboard": keyboard} if keyboard else None
        return self.post("sendMessage", chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=markup,
                         disable_web_page_preview=True)

    def edit_keyboard(self, chat_id: int, message_id: int, keyboard: List[List[Dict[str, str]]]) -> None:
        self.post("editMessageReplyMarkup", chat_id=chat_id, message_id=message_id, reply_markup={"inline_keyboard": keyboard})

    def answer(self, callback_id: str, text: Optional[str] = None) -> None:
        self.post("answerCallbackQuery", callback_query_id=callback_id, text=text)

    def updates(self, offset: Optional[int], timeout: int = 30) -> List[Dict[str, Any]]:
        return self.post("getUpdates", offset=offset, timeout=timeout, allowed_updates=["message", "callback_query"])


class TelegramError(Exception):
    def __init__(self, code: Optional[int], description: str):
        super().__init__(f"{code}: {description}")
        self.code = code


# ───────────────────────────────────────────────────────────── keyboards
def lang_keyboard():
    return [[{"text": "English", "callback_data": "lang:en"}, {"text": "ಕನ್ನಡ", "callback_data": "lang:kn"},
             {"text": "हिंदी", "callback_data": "lang:hi"}]]


def district_keyboard(lang: str):
    rows = []
    for did in DISTRICT_ORDER:
        d = registry.DISTRICTS[did]
        rows.append([{"text": {"kn": d.name_kn, "hi": d.name_hi}.get(lang) or d.name, "callback_data": f"dist:{did}"}])
    return rows


def crops_keyboard(lang: str, chosen: List[str]):
    btn = [{"text": ("✅ " if c in chosen else "") + digest.CROP_NAMES[lang][c], "callback_data": f"crop:{c}"} for c in digest.CROPS]
    return [btn[:3], btn[3:], [{"text": m("done_btn", lang), "callback_data": "done"}]]


# ───────────────────────────────────────────────────────────── conversation
def _parse_query(text: str):
    """Crops and a district named in free text, in English, Kannada or Hindi."""
    low = text.lower()
    crops = [c for c in digest.CROPS if any(digest.CROP_NAMES[l][c].lower() in low for l in digest.LANGS) or c in low]
    district = None
    for d in registry.DISTRICTS.values():
        if any(n and n.lower() in low for n in (d.id.replace("_", " "), d.name, d.name_kn, d.name_hi)):
            district = d.id
            break
    if district is None:
        for mm in registry.MANDIS.values():
            if any(n and n.lower() in low for n in (mm.name.split(",")[0], mm.name_kn, mm.name_hi)):
                district = mm.district
                break
    return crops, district


def send_digest(client: Client, sub: Dict[str, Any], crops: Optional[List[str]] = None, district: Optional[str] = None,
                kind: str = "on_demand") -> bool:
    chat = sub["chat_id"]
    text = digest.build_digest(district or sub["district"], crops or sub["crops"], sub.get("lang", "en"))
    try:
        res = client.send(chat, text)
        store.log({"chat_id": chat, "kind": kind, "status": "sent", "message_id": res.get("message_id"), "chars": len(text)})
        return True
    except TelegramError as exc:
        store.log({"chat_id": chat, "kind": kind, "status": "failed", "error": str(exc)})
        if exc.code == 403:            # the user blocked the bot
            store.upsert(chat, subscribed=False)
        return False


def handle(client: Client, update: Dict[str, Any]) -> None:
    if "callback_query" in update:
        return _callback(client, update["callback_query"])
    msg = update.get("message") or {}
    chat = (msg.get("chat") or {}).get("id")
    text = (msg.get("text") or "").strip()
    if not chat or not text:
        return
    sub = store.get(chat)
    lang = (sub or {}).get("lang", "en")
    cmd = text.split()[0].split("@")[0].lower()
    if cmd in ("/start", "/settings"):
        store.upsert(chat, first_name=(msg.get("from") or {}).get("first_name", ""), step="lang")
        client.send(chat, M["welcome"], lang_keyboard())
    elif cmd == "/stop":
        store.upsert(chat, subscribed=False)
        client.send(chat, m("stopped", lang))
    elif cmd == "/help":
        client.send(chat, m("help", lang))
    elif cmd == "/today":
        if sub and sub.get("district") and sub.get("crops"):
            send_digest(client, sub)
        else:
            client.send(chat, M["welcome"], lang_keyboard())
    else:
        crops, district = _parse_query(text)
        base = sub or {"chat_id": chat, "lang": lang}
        if not crops and not district:
            client.send(chat, m("not_understood", lang) + "\n\n" + m("help", lang))
            return
        send_digest(client, base, crops or base.get("crops") or ["tomato"], district or base.get("district") or "kolar", kind="query")


def _callback(client: Client, cq: Dict[str, Any]) -> None:
    chat = cq["message"]["chat"]["id"]
    mid = cq["message"]["message_id"]
    data = cq.get("data", "")
    sub = store.get(chat) or store.upsert(chat)
    lang = sub.get("lang", "en")
    if data.startswith("lang:"):
        lang = data.split(":", 1)[1]
        store.upsert(chat, lang=lang, step="district")
        client.answer(cq["id"])
        client.send(chat, m("district", lang), district_keyboard(lang))
    elif data.startswith("dist:"):
        store.upsert(chat, district=data.split(":", 1)[1], step="crops")
        client.answer(cq["id"])
        client.send(chat, m("crops", lang), crops_keyboard(lang, sub.get("crops", [])))
    elif data.startswith("crop:"):
        c = data.split(":", 1)[1]
        chosen = list(sub.get("crops", []))
        chosen = [x for x in chosen if x != c] if c in chosen else chosen + [c]
        store.upsert(chat, crops=chosen)
        client.answer(cq["id"])
        client.edit_keyboard(chat, mid, crops_keyboard(lang, chosen))
    elif data == "done":
        if not sub.get("crops"):
            client.answer(cq["id"], m("pick_one", lang))
            return
        sub = store.upsert(chat, subscribed=True, step="done")
        client.answer(cq["id"])
        client.send(chat, m("subscribed", lang))
        send_digest(client, sub, kind="welcome")


def run_polling(client: Optional[Client] = None) -> None:
    client = client or Client()
    me = client.post("getMe")
    logger.info("telegram bot @%s polling", me.get("username"))
    print(f"MandiSense bot @{me.get('username')} is running. Open https://t.me/{me.get('username')} and press Start. Ctrl+C to stop.")
    offset = None
    while True:
        try:
            for upd in client.updates(offset):
                offset = upd["update_id"] + 1
                try:
                    handle(client, upd)
                except Exception as exc:  # one bad update must not stop the bot
                    logger.exception("update %s failed: %s", upd.get("update_id"), exc)
        except requests.RequestException as exc:
            logger.warning("polling error: %s; retrying", exc)
            time.sleep(3)


def broadcast(client: Optional[Client] = None, dry_run: bool = False) -> Dict[str, int]:
    """Send the digest to every active subscriber (the 7 am job)."""
    subs = store.active()
    sent = failed = 0
    if dry_run:
        for s in subs:
            print(f"--- to {s['chat_id']} ({s.get('first_name', '')}, {s['lang']}, {s['district']})")
            print(digest.build_digest(s["district"], s["crops"], s["lang"]))
        return {"subscribers": len(subs), "sent": 0, "failed": 0}
    client = client or Client()
    for s in subs:
        ok = send_digest(client, s, kind="daily")
        sent += ok
        failed += not ok
        time.sleep(0.05)
    return {"subscribers": len(subs), "sent": sent, "failed": failed}
