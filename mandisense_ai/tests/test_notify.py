"""Farmer digest and the Telegram conversation, with a fake Bot API client (no network)."""

from datetime import date

import pytest

from mandisense_ai.farmer import world
from mandisense_ai.notify import digest, store, telegram

pytestmark = pytest.mark.skipif(not world.MARKET_PANEL.exists(), reason="market panel not built")


class FakeClient:
    def __init__(self):
        self.sent, self.edits, self.answers = [], [], []

    def send(self, chat_id, text, keyboard=None):
        self.sent.append({"chat_id": chat_id, "text": text, "keyboard": keyboard})
        return {"message_id": len(self.sent)}

    def edit_keyboard(self, chat_id, message_id, keyboard):
        self.edits.append(keyboard)

    def answer(self, callback_id, text=None):
        self.answers.append(text)


@pytest.fixture(autouse=True)
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "_dir", lambda: tmp_path)


def test_digest_dates_every_price_and_says_how_old_the_data_is():
    asof = digest.data_as_of()
    text = digest.build_digest("kolar", ["tomato"], "en", today=date.fromordinal(asof.toordinal() + 5))
    assert asof.strftime("%d-%b-%Y") in text
    assert "5 days old" in text
    assert "[" in text and "]" in text          # the date of the reported price


def test_advice_only_where_the_evidence_is_strong():
    text = digest.build_digest("kolar", ["potato", "garlic"], "en")
    assert "Best place to sell" not in text
    assert text.count("Prices only") == 2


def test_strong_crop_gets_a_recommendation_with_a_floor():
    text = digest.build_digest("kolar", ["tomato"], "en")
    assert "Best place to sell" in text or "farm gate" in text
    assert "9 days in 10" in text


def test_kannada_digest_uses_kannada_labels():
    text = digest.build_digest("kolar", ["tomato"], "kn")
    assert "ಟೊಮೆಟೊ" in text and "ಮಂಡಿಸೆನ್ಸ್" in text


def test_free_text_query_finds_crop_and_place():
    assert telegram._parse_query("tomato kolar") == (["tomato"], "kolar")
    crops, district = telegram._parse_query("ಈರುಳ್ಳಿ ಚಿಂತಾಮಣಿ")
    assert crops == ["onion"] and district == "chikkaballapur"


def _msg(chat, text):
    return {"message": {"chat": {"id": chat}, "from": {"first_name": "Test"}, "text": text}}


def _cb(chat, data):
    return {"callback_query": {"id": "q", "data": data, "message": {"chat": {"id": chat}, "message_id": 1}}}


def test_onboarding_subscribes_and_sends_the_first_digest():
    c = FakeClient()
    for upd in [_msg(7, "/start"), _cb(7, "lang:en"), _cb(7, "dist:kolar"), _cb(7, "crop:tomato"), _cb(7, "done")]:
        telegram.handle(c, upd)
    sub = store.get(7)
    assert sub["subscribed"] and sub["district"] == "kolar" and sub["crops"] == ["tomato"]
    assert "MandiSense market update" in c.sent[-1]["text"]
    assert store.read_log()[-1]["status"] == "sent"


def test_done_without_a_crop_is_refused():
    c = FakeClient()
    for upd in [_msg(8, "/start"), _cb(8, "lang:en"), _cb(8, "dist:kolar"), _cb(8, "done")]:
        telegram.handle(c, upd)
    assert not store.get(8).get("subscribed")
    assert c.answers[-1] == "Select at least one crop."


def test_stop_unsubscribes_and_broadcast_skips_them():
    c = FakeClient()
    for upd in [_msg(9, "/start"), _cb(9, "lang:kn"), _cb(9, "dist:kolar"), _cb(9, "crop:onion"), _cb(9, "done"), _msg(9, "/stop")]:
        telegram.handle(c, upd)
    assert store.active() == []
    assert telegram.broadcast(client=c)["subscribers"] == 0
