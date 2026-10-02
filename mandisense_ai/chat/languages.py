"""
Language handling for the chatbots.

Each reply must be in the language the user chose (Kannada, Hindi or English).
This module owns three things: the language list and the names the model is
told to write in, a script check that verifies a reply really is in the target
language, and normalisation of Kannada / Devanagari digits so numbers typed in
a local script are understood.
"""

from __future__ import annotations

import re
from typing import Dict

LANGS = ("en", "kn", "hi")
DEFAULT_LANG = "en"

LANG_NAME: Dict[str, str] = {
    "en": "English",
    "kn": "Kannada (ಕನ್ನಡ)",
    "hi": "Hindi (हिन्दी)",
}

# Unicode blocks for the two non-Latin scripts we serve.
_KN = (0x0C80, 0x0CFF)
_HI = (0x0900, 0x097F)

_DIGIT_MAP = {ord(c): str(i) for i, c in enumerate("೦೧೨೩೪೫೬೭೮೯")}
_DIGIT_MAP.update({ord(c): str(i) for i, c in enumerate("०१२३४५६७८९")})

_URL = re.compile(r"https?://\S+")


def norm_lang(value: object) -> str:
    v = str(value or "").strip().lower()[:2]
    return v if v in LANGS else DEFAULT_LANG


def normalise_digits(text: str) -> str:
    """Kannada and Devanagari digits to ASCII, so '೧೦ ಕ್ವಿಂಟಾಲ್' reads as 10."""
    return text.translate(_DIGIT_MAP)


def _in_block(ch: str, block) -> bool:
    return block[0] <= ord(ch) <= block[1]


def script_ratio(text: str, lang: str) -> float:
    """Share of the letters in `text` that are in `lang`'s script (URLs, digits
    and punctuation are ignored). English is the share of ASCII letters."""
    letters = [c for c in _URL.sub(" ", text) if c.isalpha()]
    if not letters:
        return 1.0
    if lang == "kn":
        hits = sum(1 for c in letters if _in_block(c, _KN))
    elif lang == "hi":
        hits = sum(1 for c in letters if _in_block(c, _HI))
    else:
        hits = sum(1 for c in letters if c.isascii())
    return hits / len(letters)


def is_in_language(text: str, lang: str) -> bool:
    """A reply passes if its letters are mostly in the target script. Kannada
    and Hindi replies may carry Latin brand and unit names (Agmarknet, APMC), so
    they pass at 45%; English must be almost entirely Latin."""
    if not text.strip():
        return False
    ratio = script_ratio(text, lang)
    return ratio >= (0.85 if lang == "en" else 0.45)


def detect_script(text: str) -> str:
    """Which of our three languages a piece of text is written in (by script)."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return DEFAULT_LANG
    kn = sum(1 for c in letters if _in_block(c, _KN))
    hi = sum(1 for c in letters if _in_block(c, _HI))
    if kn / len(letters) > 0.3:
        return "kn"
    if hi / len(letters) > 0.3:
        return "hi"
    return "en"


def language_directive(lang: str) -> str:
    name = LANG_NAME[lang]
    if lang == "en":
        return "Write the whole reply in clear, simple English."
    return (
        f"Write the ENTIRE reply in {name}, in its own script. Do not answer in English or in any other "
        f"language, even if the question or the tool results are in English: translate them. Keep only "
        f"unavoidable names (Agmarknet, APMC), units and numbers as they are. Use short sentences."
    )
