"""
Keyless machine translation for the few English strings the tool-driven answers
cannot write natively: web search snippets, brief headlines and scenario labels.

Without this a Kannada or Hindi reply would quote its web results in English.
(With a hosted LLM configured, the model translates and none of this is used.)

A chain of free services, each tried in turn and skipped for a few minutes after
it fails (so a rate limit costs one slow call, not every call):
  1. MyMemory   -- set MYMEMORY_EMAIL to raise the free daily quota from 5k to 50k characters
  2. Google web endpoint via deep-translator

Results are cached. `translate` never raises: it returns None when no service
could do it, and the caller keeps the English text and says so.
"""

from __future__ import annotations

import os
import re
import time
from typing import Callable, Dict, List, Optional, Tuple

import requests

from mandisense_ai.chat.languages import is_in_language
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

_CACHE: Dict[Tuple[str, str], str] = {}
_DOWN_UNTIL: Dict[str, float] = {}
_COOLDOWN_SECONDS = 300
_MAX_CHARS = 450  # MyMemory's per-request limit


def _mymemory(text: str, lang: str) -> str:
    params = {"q": text, "langpair": f"en|{lang}"}
    email = os.getenv("MYMEMORY_EMAIL", "").strip()
    if email:
        params["de"] = email
    r = requests.get("https://api.mymemory.translated.net/get", params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    if int(data.get("responseStatus", 200)) != 200:
        raise RuntimeError(str(data.get("responseDetails", "mymemory error"))[:80])
    out = data["responseData"]["translatedText"]
    if "MYMEMORY WARNING" in out.upper():
        raise RuntimeError("mymemory quota")
    return out


def _google(text: str, lang: str) -> str:
    from deep_translator import GoogleTranslator

    return GoogleTranslator(source="en", target=lang).translate(text)


_SERVICES: List[Tuple[str, Callable[[str, str], str]]] = [("mymemory", _mymemory), ("google", _google)]


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def translate(text: str, lang: str) -> Optional[str]:
    """English -> Kannada/Hindi. None if `lang` is English, the text is empty, or every service failed."""
    if lang not in ("kn", "hi"):
        return None
    text = _clean(text)[:_MAX_CHARS]
    if not text:
        return None
    key = (lang, text)
    if key in _CACHE:
        return _CACHE[key]
    now = time.time()
    for name, fn in _SERVICES:
        if _DOWN_UNTIL.get(name, 0) > now:
            continue
        try:
            out = _clean(fn(text, lang))
            if out and is_in_language(out, lang):  # a "translation" still in English is a failure
                if len(_CACHE) > 500:
                    _CACHE.clear()
                _CACHE[key] = out
                return out
            raise RuntimeError("not translated")
        except Exception as exc:
            logger.warning("translation via %s failed: %s", name, str(exc)[:100])
            _DOWN_UNTIL[name] = now + _COOLDOWN_SECONDS
    return None
