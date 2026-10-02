"""
Tests for the farmer and trader chatbots (`mandisense_ai/chat/`).

The hosted model is replaced by a scripted fake so the tool loop, the language
rule and the grounding check can be tested without a network or an API key. The
fallback tests run against the real recorded data, like the other farmer tests.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mandisense_ai.chat import entities, fallback, grounding, languages, providers, tools, translate as tr, web
from mandisense_ai.chat.engine import handle
from mandisense_ai.chat.providers import LLMError, LLMResult, Provider, ToolCall


# ── languages ───────────────────────────────────────────────────────────────

def test_script_detection_and_language_check():
    assert languages.is_in_language("Tomato is ₹1,472 per quintal.", "en")
    assert not languages.is_in_language("Tomato is ₹1,472 per quintal.", "kn")
    assert languages.is_in_language("ಟೊಮೇಟೊ ಬೆಲೆ ₹1,472 ಆಗಿದೆ", "kn")
    assert languages.is_in_language("टमाटर का भाव ₹1,472 है", "hi")
    assert not languages.is_in_language("ಟೊಮೇಟೊ ಬೆಲೆ", "hi")
    assert languages.is_in_language("ಟೊಮೇಟೊ ಬೆಲೆ ಈಗ ಹೆಚ್ಚಾಗಿದೆ ಮತ್ತು Agmarknet ದಾಖಲೆಯ ಪ್ರಕಾರ ಸರಿ", "kn")  # brand names are allowed
    assert languages.detect_script("ಕೋಲಾರ") == "kn" and languages.detect_script("कोलार") == "hi"


def test_local_digits_are_read_as_numbers():
    assert languages.normalise_digits("೧೦ ಕ್ವಿಂಟಾಲ್") == "10 ಕ್ವಿಂಟಾಲ್"
    assert languages.normalise_digits("१५ क्विंटल") == "15 क्विंटल"


def test_norm_lang_defaults_to_english():
    assert languages.norm_lang("KN") == "kn" and languages.norm_lang("fr") == "en" and languages.norm_lang(None) == "en"


# ── entities ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text,crop", [
    ("tomato price", "tomato"), ("ಟೊಮೇಟೊ ಬೆಲೆ", "tomato"), ("प्याज का भाव", "onion"),
    ("ಬೆಳ್ಳುಳ್ಳಿ", "garlic"), ("आलू", "potato"), ("ginger rate", "ginger"), ("dry chillies", "dry_chillies"),
])
def test_crop_is_read_in_all_three_languages(text, crop):
    assert entities.extract(text).crop == crop


def test_places_quantity_and_horizon():
    e = entities.extract("Sell ೧೦ ಕ್ವಿಂಟಾಲ್ tomato in Mulbagal for 5 days")
    assert e.crop == "tomato" and e.mandi_id == "mulbagal_apmc" and e.district == "kolar"
    assert e.quantity_quintals == 10 and e.horizon_days == 5
    assert entities.extract("2 tonnes onion").quantity_quintals == 20
    assert entities.extract("कोलार में टमाटर").district == "kolar"
    assert entities.extract("ಕೋಲಾರದಲ್ಲಿ ಟೊಮೇಟೊ").district == "kolar"


def test_context_carries_over_but_a_named_place_wins():
    prev = {"crop": "onion", "district": "kolar", "mandi_id": "kolar_apmc"}
    e = entities.merge(entities.extract("and in Doddaballapur?"), prev, {})
    assert e.crop == "onion" and e.mandi_id == "doddaballapur_apmc"
    e2 = entities.merge(entities.extract("what about potato"), prev, {})
    assert e2.crop == "potato" and e2.district == "kolar"


# ── grounding ───────────────────────────────────────────────────────────────

def test_numbers_must_come_from_the_tool_results():
    out = [{"price": 1472.3, "change": -12.5, "range": [1088.0, 1872.0]}]
    ok = grounding.check("Tomato is ₹1,472, fell 12.5%, range ₹1,088 to ₹1,872.", out, [], {})
    assert ok["grounded"]
    bad = grounding.check("Tomato will reach ₹2,950 next week.", out, [], {})
    assert not bad["grounded"] and 2950.0 in bad["ungrounded"]


def test_grounding_allows_users_own_numbers_units_and_small_counts():
    assert grounding.check("For 10 quintals you get ₹14,723.", [{"total": 14723.0}], ["I have 10 quintals"], {})["grounded"]
    assert grounding.check("That is 1.5 lakh rupees.", [{"total": 150000.0}], [], {})["grounded"]  # unit change
    assert grounding.check("Over 7 days it rose.", [], [], {})["grounded"]  # small numbers are not claims


# ── web safety ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("url", ["http://localhost:8000/admin", "http://127.0.0.1/", "http://10.0.0.5/x", "http://192.168.1.1/",
                                 "http://169.254.169.254/latest/meta-data", "file:///etc/passwd", "ftp://example.com/", "javascript:alert(1)"])
def test_private_and_non_http_urls_are_refused(url):
    assert not web.is_public_url(url)
    assert "error" in web.fetch(url)


def test_search_falls_back_to_wikipedia_when_ddgs_fails(monkeypatch):
    web._CACHE.clear()
    import ddgs

    class Boom:
        def __init__(self, *a, **k): pass
        def text(self, *a, **k): raise RuntimeError("rate limited")

    monkeypatch.setattr(ddgs, "DDGS", Boom)
    monkeypatch.setattr(web, "_wikipedia", lambda q, n: [{"title": "Onion", "url": "https://en.wikipedia.org/wiki/Onion", "snippet": "A vegetable"}])
    r = web.search("onion fallback test")
    assert r["engine"] == "wikipedia" and r["results"][0]["title"] == "Onion"


def test_search_reports_unavailable_when_everything_fails(monkeypatch):
    web._CACHE.clear()
    import ddgs

    class Boom:
        def __init__(self, *a, **k): pass
        def text(self, *a, **k): raise RuntimeError("down")

    monkeypatch.setattr(ddgs, "DDGS", Boom)
    monkeypatch.setattr(web, "_wikipedia", lambda q, n: (_ for _ in ()).throw(RuntimeError("down")))
    r = web.search("nothing works zzz")
    assert r["results"] == [] and "error" in r


def test_off_topic_search_results_are_rejected():
    assert not web.is_relevant("What is the MSP for onion?", "Can an employer force you to have a photograph taken")
    assert web.is_relevant("What is the MSP for onion?", "Onion MSP hiked 13% for buffer stock")
    assert web.is_relevant("ಈರುಳ್ಳಿ ಬೆಂಬಲ ಬೆಲೆ", "anything")  # non-Latin queries cannot be word-matched


def test_search_skips_a_backend_that_returns_junk(monkeypatch):
    web._CACHE.clear()
    import ddgs

    class Fake:
        def __init__(self, *a, **k): pass
        def text(self, q, region=None, max_results=5, backend="auto"):
            if backend == "bing":
                return [{"title": "Photograph policy", "href": "https://junk.example", "body": "employer photograph"}]
            if backend == "yahoo":
                return [{"title": "Onion MSP 2026", "href": "https://good.example", "body": "minimum support price onion"}]
            raise RuntimeError("no results")

    monkeypatch.setattr(ddgs, "DDGS", Fake)
    r = web.search("What is the MSP for onion zz")
    assert r["engine"] == "yahoo" and r["results"][0]["url"] == "https://good.example"


def test_html_is_reduced_to_readable_text():
    text = web._html_to_text("<html><head><style>x{}</style></head><body><nav>menu</nav><article><h1>Title</h1><p>Body text here.</p></article><script>evil()</script></body></html>")
    assert "Title" in text and "Body text here." in text and "evil" not in text and "menu" not in text


# ── translation ─────────────────────────────────────────────────────────────

@pytest.fixture()
def clean_translator():
    tr._CACHE.clear()
    tr._DOWN_UNTIL.clear()
    yield
    tr._CACHE.clear()
    tr._DOWN_UNTIL.clear()


def test_translator_uses_the_next_service_when_one_fails_and_caches(clean_translator, monkeypatch):
    calls = []

    def bad(text, lang):
        calls.append("bad")
        raise RuntimeError("rate limited")

    def good(text, lang):
        calls.append("good")
        return "ರೈತರಿಗೆ ಆದಾಯ ಬೆಂಬಲ"

    monkeypatch.setattr(tr, "_SERVICES", [("bad", bad), ("good", good)])
    assert tr.translate("income support for farmers", "kn") == "ರೈತರಿಗೆ ಆದಾಯ ಬೆಂಬಲ"
    assert tr.translate("income support for farmers", "kn") == "ರೈತರಿಗೆ ಆದಾಯ ಬೆಂಬಲ"  # cached
    assert calls == ["bad", "good"]
    assert tr.translate("another sentence", "kn") == "ರೈತರಿಗೆ ಆದಾಯ ಬೆಂಬಲ"
    assert calls == ["bad", "good", "good"]  # the failed service is skipped for a while


def test_translator_rejects_an_untranslated_result_and_never_raises(clean_translator, monkeypatch):
    monkeypatch.setattr(tr, "_SERVICES", [("echo", lambda text, lang: text)])
    assert tr.translate("still english", "hi") is None
    assert tr.translate("anything", "en") is None and tr.translate("", "kn") is None


def test_web_answer_is_translated_into_the_users_language(clean_translator, monkeypatch):
    monkeypatch.setattr(web, "search", lambda q, n=5: {"query": q, "engine": "x", "results": [{"title": "PM-KISAN", "url": "https://pmkisan.gov.in", "snippet": "Income support"}]})
    monkeypatch.setattr(tr, "_SERVICES", [("fake", lambda text, lang: "ಪಿಎಂ-ಕಿಸಾನ್: ಆದಾಯ ಬೆಂಬಲ")])
    r = handle("farmer", "pm kisan scheme", "kn", [], {})
    assert r["intent"] == "web" and "ಆದಾಯ ಬೆಂಬಲ" in r["reply"] and languages.is_in_language(r["reply"], "kn")


def test_web_answer_says_so_when_translation_is_unavailable(clean_translator, monkeypatch):
    monkeypatch.setattr(web, "search", lambda q, n=5: {"query": q, "engine": "x", "results": [{"title": "PM-KISAN", "url": "https://pmkisan.gov.in", "snippet": "Income support"}]})
    monkeypatch.setattr(tr, "_SERVICES", [])
    r = handle("farmer", "pm kisan scheme", "hi", [], {})
    assert "अनुवाद नहीं हो सका" in r["reply"] and "Income support" in r["reply"]


# ── tools ───────────────────────────────────────────────────────────────────

def test_every_tool_has_a_valid_schema_and_a_persona():
    names = [t.name for t in tools.TOOLS]
    assert len(names) == len(set(names))
    for t in tools.TOOLS:
        assert t.description and t.parameters["type"] == "object" and t.personas
        for req in t.parameters["required"]:
            assert req in t.parameters["properties"]


def test_personas_only_get_their_own_tools():
    farmer, trader = {t.name for t in tools.tools_for("farmer")}, {t.name for t in tools.tools_for("trader")}
    assert "get_sell_plan" in farmer and "get_sell_plan" not in trader
    assert "scan_spreads" in trader and "scan_spreads" not in farmer
    assert {"web_search", "fetch_url", "get_weather", "calculator"} <= farmer & trader
    assert "error" in tools.run_tool("scan_spreads", {"crop": "tomato"}, "farmer")  # refused for the wrong persona


def test_calculator_is_exact_and_safe():
    assert tools.run_tool("calculator", {"expression": "10 * 1,472.3"}, "farmer")["result"] == 14723.0
    for evil in ("__import__('os').system('echo hi')", "open('x')", "().__class__", "9**9**9**9", "10**100", "9" * 200, "2**(2**20)"):
        assert "error" in tools.run_tool("calculator", {"expression": evil}, "farmer"), evil


def test_tools_never_raise():
    assert "error" in tools.run_tool("get_price_board", {"crop": "tomato"}, "farmer")  # missing argument
    assert "error" in tools.run_tool("no_such_tool", {}, "farmer")


# ── providers ───────────────────────────────────────────────────────────────

def test_provider_is_chosen_from_the_environment(monkeypatch):
    for k in ("ANTHROPIC_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY", "CHAT_PROVIDER", "CHAT_MODEL"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setattr(providers, "load_dotenv", lambda: None, raising=False)
    assert providers.get_provider() is None
    monkeypatch.setenv("GROQ_API_KEY", "g")
    assert providers.get_provider().name == "groq"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a")
    assert providers.get_provider().name == "anthropic"
    monkeypatch.setenv("CHAT_PROVIDER", "none")
    assert providers.get_provider() is None
    monkeypatch.setenv("CHAT_PROVIDER", "groq")
    monkeypatch.setenv("CHAT_MODEL", "my-model")
    p = providers.get_provider()
    assert p.name == "groq" and p.model == "my-model"


# ── engine with a scripted model ────────────────────────────────────────────

class Scripted(Provider):
    name, model = "fake", "fake-1"

    def __init__(self, steps: List[Any]):
        self.steps, self.calls = list(steps), []

    def complete(self, system, messages, tools, max_tokens=1100):
        self.calls.append({"system": system, "messages": json.loads(json.dumps(messages, default=str)), "tools": [t.name for t in tools]})
        step = self.steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


def test_llm_tool_loop_answers_from_tool_results():
    fake = Scripted([
        LLMResult(tool_calls=[ToolCall("c1", "get_price_board", {"crop": "tomato", "district": "kolar"})]),
        LLMResult(text="Tomato in Kolar is about ₹1,472 per quintal."),
    ])
    r = handle("farmer", "tomato price in Kolar?", "en", [], {}, provider=fake)
    assert r["mode"] == "llm" and r["provider"] == "fake"
    assert [c["tool"] for c in r["tools_used"]] == ["get_price_board"] and r["tools_used"][0]["ok"]
    assert "get_sell_plan" in fake.calls[0]["tools"] and "scan_spreads" not in fake.calls[0]["tools"]
    tool_msg = [m for m in fake.calls[1]["messages"] if m["role"] == "tool"][0]
    assert "price_per_quintal" in tool_msg["content"]
    assert "English" in fake.calls[0]["system"] and "web_search" in fake.calls[0]["system"]


def test_reply_in_the_wrong_language_is_rewritten_once():
    fake = Scripted([LLMResult(text="Tomato is ₹1,472."), LLMResult(text="ಟೊಮೇಟೊ ₹1,472 ಆಗಿದೆ.")])
    r = handle("farmer", "ಟೊಮೇಟೊ", "kn", [], {}, provider=fake)
    assert r["mode"] == "llm" and "ಟೊಮೇಟೊ" in r["reply"]


def test_a_reply_that_stays_in_the_wrong_language_falls_back_to_the_native_answer():
    fake = Scripted([LLMResult(text="Tomato is fine."), LLMResult(text="Still English.")])
    r = handle("farmer", "ಕೋಲಾರದಲ್ಲಿ ಟೊಮೇಟೊ ಬೆಲೆ ಎಷ್ಟು?", "kn", [], {}, provider=fake)
    assert r["mode"] == "tools" and r["note"] == "llm_reply_rejected" and languages.is_in_language(r["reply"], "kn")


def test_llm_failure_degrades_to_the_tool_answer():
    r = handle("farmer", "tomato price in Kolar?", "en", [], {}, provider=Scripted([LLMError("HTTP 401")]))
    assert r["mode"] == "tools" and r["note"] == "llm_unavailable" and "₹" in r["reply"]


def test_invented_numbers_are_reported():
    fake = Scripted([LLMResult(text="Tomato will hit ₹9,999 per quintal tomorrow.")])
    r = handle("farmer", "tomato?", "en", [], {}, provider=fake)
    assert not r["grounded"] and 9999.0 in r["ungrounded_numbers"]


def test_history_and_ui_context_reach_the_model():
    fake = Scripted([LLMResult(text="Onion is fine.")])
    handle("farmer", "and onion?", "en", [{"role": "user", "content": "tomato in Kolar"}, {"role": "assistant", "content": "It is ₹1,472."}],
           {"district": "kolar"}, provider=fake)
    sent = fake.calls[0]["messages"]
    assert [m["role"] for m in sent] == ["user", "assistant", "user"] and "kolar" in fake.calls[0]["system"]


# ── fallback answers, per language ──────────────────────────────────────────

@pytest.mark.parametrize("lang,q", [("en", "What is tomato worth in Kolar?"), ("kn", "ಕೋಲಾರದಲ್ಲಿ ಟೊಮೇಟೊ ಬೆಲೆ ಎಷ್ಟು?"), ("hi", "कोलार में टमाटर का भाव क्या है?")])
def test_farmer_price_answer_is_in_the_chosen_language_and_grounded(lang, q):
    r = handle("farmer", q, lang, [], {})
    assert r["intent"] == "price" and languages.is_in_language(r["reply"], lang) and r["grounded"]
    assert "₹" in r["reply"] and r["context"]["crop"] == "tomato"


def test_a_bare_greeting_is_not_priced_with_a_carried_crop():
    r = handle("farmer", "नमस्ते", "hi", [], {"last_entities": {"crop": "onion", "district": "kolar"}})
    assert r["intent"] == "help" and "₹" not in r["reply"]


def test_a_scheme_question_goes_to_the_web_not_the_sell_planner(monkeypatch):
    monkeypatch.setattr(web, "search", lambda q, n=5: {"query": q, "engine": "x", "results": [{"title": "PM-KISAN", "url": "https://pmkisan.gov.in", "snippet": "Income support"}]})
    r = handle("farmer", "ಪಿಎಂ ಕಿಸಾನ್ ಯೋಜನೆ ಬಗ್ಗೆ ಹೇಳಿ", "kn", [], {"last_entities": {"crop": "tomato"}})
    assert r["intent"] == "web" and r["sources"][0]["url"] == "https://pmkisan.gov.in"


def test_strong_sell_words_ask_hold_or_sell_with_the_quantity():
    r = handle("farmer", "Should I hold 10 quintals of tomato in Kolar?", "en", [], {})
    assert r["intent"] == "hold_or_sell" and "10 quintals" in r["reply"]


def test_missing_crop_is_asked_for_not_guessed():
    r = handle("farmer", "what is the price", "en", [], {})
    assert r["intent"] == "clarify" and "Which crop" in r["reply"]


def test_weather_goes_to_the_weather_tool(monkeypatch):
    monkeypatch.setattr(web, "weather", lambda *a, **k: {"place": "Kolar", "days": [{"date": "2026-10-03", "max_c": 29.0, "min_c": 19.0, "rain_mm": 0.0, "summary": "overcast"}], "source": "Open-Meteo"})
    r = handle("farmer", "ಕೋಲಾರದಲ್ಲಿ ಮಳೆ ಬರುತ್ತದೆಯೇ?", "kn", [], {})
    assert r["intent"] == "weather" and "ಕೋಲಾರ" in r["reply"] and r["sources"][0]["title"] == "Open-Meteo"


@pytest.mark.parametrize("q,intent", [
    ("Is the tomato spread worth the trip?", "spreads"), ("Any district gap worth hauling for tomato?", "gap"),
    ("What is the volatility regime for tomato at Kolar?", "volatility"), ("Find analogs for onion at Kolar", "analogs"),
    ("Which scenarios are active for tomato in Kolar?", "scenarios"), ("Forward price for tomato 3 days at Kolar", "forward"),
    ("Give me the decision brief for tomato Kolar", "brief"),
])
def test_trader_questions_run_the_matching_desk_tool(q, intent):
    r = handle("trader", q, "en", [], {})
    assert r["intent"] == intent and r["tools_used"] and r["tools_used"][0]["ok"] and r["grounded"]


def test_trader_answer_in_hindi():
    r = handle("trader", "कोलार में टमाटर की अस्थिरता कैसी है?", "hi", [], {})
    assert r["intent"] == "volatility" and languages.is_in_language(r["reply"], "hi")


def test_rupee_formatting_uses_indian_grouping():
    assert fallback.inr(147230) == "₹1,47,230" and fallback.inr(1472.3) == "₹1,472" and fallback.inr(-39) == "−₹39"


# ── HTTP ────────────────────────────────────────────────────────────────────

@pytest.fixture()
def client():
    from api import chat_router

    app = FastAPI()
    app.include_router(chat_router.router)
    return TestClient(app)


def test_chat_endpoint_round_trip(client):
    r = client.post("/v1/chat", json={"persona": "farmer", "message": "tomato price in Kolar", "lang": "en"})
    assert r.status_code == 200
    body = r.json()
    assert body["reply"] and body["lang"] == "en" and body["mode"] in ("llm", "tools") and "suggestions" in body and "context" in body


def test_chat_endpoint_validates_input(client):
    assert client.post("/v1/chat", json={"persona": "admin", "message": "x"}).status_code == 422
    assert client.post("/v1/chat", json={"persona": "farmer", "message": "x", "lang": "fr"}).status_code == 422
    assert client.post("/v1/chat", json={"persona": "farmer", "message": ""}).status_code == 422
    assert client.post("/v1/chat", json={"persona": "farmer", "message": "x" * 1001}).status_code == 422


def test_status_endpoint_lists_tools_per_persona(client):
    body = client.get("/v1/chat/status").json()
    assert body["languages"] == ["en", "kn", "hi"] and body["web_search"] is True
    assert "get_sell_plan" in body["tools"]["farmer"] and "scan_spreads" in body["tools"]["trader"]
