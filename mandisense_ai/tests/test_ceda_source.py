"""
Tests for the CEDA Agmarknet client.

No key exists yet (see the module docstring on `ceda.py`), so every test
here drives the client through a fake `Transport` — a plain function
returning exactly the JSON shape CEDA's own published OpenAPI spec
declares for each endpoint (extracted directly from
`https://api.ceda.ashoka.edu.in/documentation/`, not guessed) — rather than
touching the network. What these tests verify is request-building and
response-parsing correctness; whether the live server's real responses
actually match its own published schema is the one thing that cannot be
checked here and should be watched on the first live run.
"""

from __future__ import annotations

import json
import urllib.error

import pytest

from mandisense_ai.forecasting.sources import ceda
from mandisense_ai.utils.exceptions import ConfigurationError


@pytest.fixture(autouse=True)
def _no_real_sleep(monkeypatch):
    """Retry backoff is real (2s, 4s, ...) in production on purpose; tests
    exercise the retry *logic*, not the wait, so time.sleep is a no-op here."""
    monkeypatch.setattr(ceda.time, "sleep", lambda seconds: None)


# ── auth ──────────────────────────────────────────────────────────────────


def test_get_api_key_raises_when_unset(monkeypatch):
    monkeypatch.delenv("CEDA_API_KEY", raising=False)
    with pytest.raises(ConfigurationError):
        ceda.get_api_key()


def test_get_api_key_returns_the_real_value(monkeypatch):
    monkeypatch.setenv("CEDA_API_KEY", "secret-token")
    assert ceda.get_api_key() == "secret-token"


def test_is_configured_reflects_the_env_var(monkeypatch):
    monkeypatch.delenv("CEDA_API_KEY", raising=False)
    assert ceda.is_configured() is False
    monkeypatch.setenv("CEDA_API_KEY", "x")
    assert ceda.is_configured() is True


def test_default_transport_sends_a_bearer_token(monkeypatch):
    """The one piece of `_default_transport` a fake Transport can't cover:
    that the real urllib path actually attaches the key as a bearer token."""
    monkeypatch.setenv("CEDA_API_KEY", "secret-token")
    captured = {}

    class _FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"commodities": []}).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["headers"] = dict(request.headers)
        captured["url"] = request.full_url
        captured["method"] = request.get_method()
        return _FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    ceda._default_transport("GET", "/agmarknet/commodities", None)

    assert captured["headers"]["Authorization"] == "Bearer secret-token"
    assert captured["url"] == f"{ceda.BASE_URL}/agmarknet/commodities"
    assert captured["method"] == "GET"


# ── retry / error handling ────────────────────────────────────────────────


def test_request_retries_on_a_generic_failure_then_succeeds():
    calls = {"n": 0}

    def flaky(method, path, body):
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("boom")
        return {"ok": True}

    result = ceda._request("GET", "/x", transport=flaky)
    assert result == {"ok": True}
    assert calls["n"] == 3


def test_a_nested_cedafetcherror_is_not_retried_again():
    """A CedaFetchError raised inside a call already represents an exhausted
    retry budget (or an intentional terminal signal, e.g. from
    `resolve_market_ids`) -- retrying it a second time would just repeat
    whatever already failed once for no benefit."""
    calls = {"n": 0}

    def raises_terminal(method, path, body):
        calls["n"] += 1
        raise ceda.CedaFetchError("already gave up once")

    with pytest.raises(ceda.CedaFetchError, match="already gave up once"):
        ceda._request("GET", "/x", transport=raises_terminal)
    assert calls["n"] == 1


def test_request_raises_after_exhausting_retries():
    def always_fails(method, path, body):
        raise ConnectionError("still down")

    with pytest.raises(ceda.CedaFetchError):
        ceda._request("GET", "/x", transport=always_fails)


def test_a_401_is_not_retried_and_surfaces_the_servers_message():
    """An expired/missing key will not fix itself on retry #2 -- confirmed
    live against the real API (see the ceda.py module docstring): it
    answers 401 with `{"message": "Unauthorised, no api key passed."}` and
    an invalid key with `{"message": "Api key expired"}`, not a 5xx."""
    calls = {"n": 0}

    def unauthorised(method, path, body):
        calls["n"] += 1
        error_body = json.dumps({"message": "Api key expired"}).encode("utf-8")
        raise urllib.error.HTTPError(
            url="x", code=401, msg="Unauthorized",
            hdrs=None, fp=__import__("io").BytesIO(error_body),
        )

    with pytest.raises(ceda.CedaFetchError, match="Api key expired"):
        ceda._request("GET", "/x", transport=unauthorised)
    assert calls["n"] == 1  # no retry on an auth failure


# ── metadata parsing (exact shapes from CEDA's published OpenAPI spec) ───


COMMODITIES_RESPONSE = {
    "commodities": [
        {"id": 1, "name": "Absinthe"},
        {"id": 65, "name": "Tomato"},
        {"id": 23, "name": "Onion"},
        {"id": 999, "name": "Not A Real Crop"},
    ]
}

GEOGRAPHIES_RESPONSE = {
    "geographies": [
        {
            "state_id": 16,
            "state_name": "Karnataka",
            "districts": [
                {"district_id": 242, "district_name": "Kolar"},
                {"district_id": 246, "district_name": "Bangalore Urban"},
            ],
        },
        {"state_id": 20, "state_name": "Maharashtra", "districts": []},
    ]
}


def test_fetch_commodities_keeps_only_recognised_tracked_crops():
    result = ceda.fetch_commodities(transport=lambda m, p, b: COMMODITIES_RESPONSE)
    assert result.get("tomato") == 65
    assert result.get("onion") == 23
    assert "not_a_real_crop" not in result
    assert 1 not in result.values()  # Absinthe: not a tracked commodity


def test_fetch_geographies_nests_districts_under_their_state():
    result = ceda.fetch_geographies(transport=lambda m, p, b: GEOGRAPHIES_RESPONSE)
    assert result["Karnataka"]["state_id"] == 16
    assert result["Karnataka"]["districts"]["Kolar"] == 242
    assert result["Maharashtra"]["districts"] == {}


def test_fetch_markets_posts_the_documented_request_shape():
    captured = {}

    def fake(method, path, body):
        captured["method"], captured["path"], captured["body"] = method, path, body
        return {"data": [{"census_state_id": 16, "census_district_id": 242,
                           "market_id": 744, "market_name": "Bangarpet APMC"}]}

    result = ceda.fetch_markets(65, 16, 242, indicator="price", transport=fake)
    assert captured["method"] == "POST"
    assert captured["path"] == "/agmarknet/markets"
    assert captured["body"] == {"commodity_id": 65, "state_id": 16, "district_id": 242, "indicator": "price"}
    assert result[0]["market_id"] == 744


# ── market resolution (name -> id, through the shared alias table) ────────


def test_resolve_market_ids_matches_through_the_canonical_alias_table():
    def fake(method, path, body):
        district = body["district_id"]
        if district == 242:
            return {"data": [{"market_id": 744, "market_name": "Bangarpet APMC"}]}
        return {"data": [{"market_id": 991, "market_name": "Yeshwanthpur APMC"}]}

    resolved = ceda.resolve_market_ids(
        mandi_ids=["bangarpet_apmc", "bangalore_yeshwanthpur"],
        commodity_id=65, state_id=16, district_ids=[242, 246],
        transport=fake,
    )
    assert resolved == {"bangarpet_apmc": 744, "bangalore_yeshwanthpur": 991}


def test_resolve_market_ids_stops_once_everything_wanted_is_found():
    calls = []

    def fake(method, path, body):
        calls.append(body["district_id"])
        return {"data": [{"market_id": 744, "market_name": "Bangarpet APMC"}]}

    ceda.resolve_market_ids(
        mandi_ids=["bangarpet_apmc"], commodity_id=65, state_id=16,
        district_ids=[242, 246, 999], transport=fake,
    )
    assert calls == [242]  # never looked at the remaining districts


def test_resolve_market_ids_tolerates_one_district_failing():
    def fake(method, path, body):
        if body["district_id"] == 242:
            raise ceda.CedaFetchError("district lookup failed")
        return {"data": [{"market_id": 991, "market_name": "Yeshwanthpur APMC"}]}

    resolved = ceda.resolve_market_ids(
        mandi_ids=["bangalore_yeshwanthpur"], commodity_id=65, state_id=16,
        district_ids=[242, 246], transport=fake,
    )
    assert resolved == {"bangalore_yeshwanthpur": 991}


def test_unrecognised_market_names_are_not_matched_to_anything():
    def fake(method, path, body):
        return {"data": [{"market_id": 1, "market_name": "Some Unrelated Yard"}]}

    resolved = ceda.resolve_market_ids(
        mandi_ids=["bangarpet_apmc"], commodity_id=65, state_id=16,
        district_ids=[242], transport=fake,
    )
    assert resolved == {}


# ── prices + quantities merge ──────────────────────────────────────────────


def _merge_fixture():
    """A transport that answers every call this module makes for one
    (state, commodity) slice with one resolvable market."""
    def fake(method, path, body):
        if path == "/agmarknet/commodities":
            return {"commodities": [{"id": 65, "name": "Tomato"}]}
        if path == "/agmarknet/geographies":
            return {"geographies": [{
                "state_id": 16, "state_name": "Karnataka",
                "districts": [{"district_id": 242, "district_name": "Kolar"}],
            }]}
        if path == "/agmarknet/markets":
            return {"data": [{"market_id": 744, "market_name": "Bangarpet APMC"}]}
        if path == "/agmarknet/prices":
            return {"data": [
                {"date": "2026-01-01", "min_price": 900.0, "max_price": 1100.0, "modal_price": 1000.0},
                {"date": "2026-01-02", "min_price": None, "max_price": None, "modal_price": None},
            ]}
        if path == "/agmarknet/quantities":
            return {"data": [{"date": "2026-01-01", "quantity": 250.5}]}
        raise AssertionError(f"unexpected path {path}")
    return fake


def test_merges_prices_and_quantities_on_the_same_date():
    frame = ceda.fetch_daily_prices_and_arrivals(
        "2026-01-01", "2026-01-02",
        states=["Karnataka"], commodities=["tomato"], mandi_ids=["bangarpet_apmc"],
        transport=_merge_fixture(),
    )
    assert len(frame) == 1  # the null-price row is dropped
    row = frame.iloc[0]
    assert row["commodity"] == "tomato"
    assert row["mandi_id"] == "bangarpet_apmc"
    assert row["modal_price"] == 1000.0
    assert row["arrivals"] == 250.5
    assert row["source"] == "ceda_agmarknet"


def test_a_price_date_with_no_matching_quantity_gets_a_null_arrival():
    def fake(method, path, body):
        base = _merge_fixture()(method, path, body)
        if path == "/agmarknet/quantities":
            return {"data": []}  # no arrival data for this market at all
        return base

    frame = ceda.fetch_daily_prices_and_arrivals(
        "2026-01-01", "2026-01-02",
        states=["Karnataka"], commodities=["tomato"], mandi_ids=["bangarpet_apmc"],
        transport=fake,
    )
    assert frame.iloc[0]["arrivals"] is None


def test_rows_missing_a_modal_price_are_skipped_not_coerced():
    frame = ceda.fetch_daily_prices_and_arrivals(
        "2026-01-01", "2026-01-02",
        states=["Karnataka"], commodities=["tomato"], mandi_ids=["bangarpet_apmc"],
        transport=_merge_fixture(),
    )
    assert frame["modal_price"].notna().all()


def test_a_state_with_no_ceda_geography_entry_is_skipped_not_fatal():
    def fake(method, path, body):
        if path == "/agmarknet/commodities":
            return {"commodities": [{"id": 65, "name": "Tomato"}]}
        if path == "/agmarknet/geographies":
            return {"geographies": []}  # no entry for the requested state at all
        raise AssertionError(f"should not reach {path}")

    frame = ceda.fetch_daily_prices_and_arrivals(
        "2026-01-01", "2026-01-02",
        states=["Karnataka"], commodities=["tomato"], mandi_ids=["bangarpet_apmc"],
        transport=fake,
    )
    assert frame.empty


def test_raises_only_when_every_slice_failed():
    def all_fail(method, path, body):
        if path == "/agmarknet/commodities":
            return {"commodities": [{"id": 65, "name": "Tomato"}]}
        if path == "/agmarknet/geographies":
            return {"geographies": [{
                "state_id": 16, "state_name": "Karnataka",
                "districts": [{"district_id": 242, "district_name": "Kolar"}],
            }]}
        raise ceda.CedaFetchError("down")

    with pytest.raises(ceda.CedaFetchError, match="All CEDA slices failed"):
        ceda.fetch_daily_prices_and_arrivals(
            "2026-01-01", "2026-01-02",
            states=["Karnataka"], commodities=["tomato"], mandi_ids=["bangarpet_apmc"],
            transport=all_fail,
        )


def test_one_failing_commodity_does_not_fail_a_run_with_others(monkeypatch):
    def fake(method, path, body):
        if path == "/agmarknet/commodities":
            return {"commodities": [{"id": 65, "name": "Tomato"}, {"id": 23, "name": "Onion"}]}
        if path == "/agmarknet/geographies":
            return {"geographies": [{
                "state_id": 16, "state_name": "Karnataka",
                "districts": [{"district_id": 242, "district_name": "Kolar"}],
            }]}
        if path == "/agmarknet/markets" and body["commodity_id"] == 23:
            raise ceda.CedaFetchError("onion markets down")
        if path == "/agmarknet/markets":
            return {"data": [{"market_id": 744, "market_name": "Bangarpet APMC"}]}
        if path == "/agmarknet/prices":
            return {"data": [{"date": "2026-01-01", "min_price": 900.0, "max_price": 1100.0, "modal_price": 1000.0}]}
        if path == "/agmarknet/quantities":
            return {"data": []}
        raise AssertionError(path)

    frame = ceda.fetch_daily_prices_and_arrivals(
        "2026-01-01", "2026-01-02",
        states=["Karnataka"], commodities=["tomato", "onion"], mandi_ids=["bangarpet_apmc"],
        transport=fake,
    )
    assert set(frame["commodity"]) == {"tomato"}
