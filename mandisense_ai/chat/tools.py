"""
The tools the chatbots can call.

Every farmer and trader feature in the app is a tool here, wrapping the same
Python function the HTTP endpoints use, so a chat answer and the matching
screen can never disagree. Web tools (search, fetch, weather) cover everything
the mandi records cannot. Tool results are trimmed so they fit a model's
context, and every tool returns a plain dict (errors included), never raises.
"""

from __future__ import annotations

import ast
import json
import operator
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from mandisense_ai.chat import web
from mandisense_ai.farmer import registry
from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

MAX_RESULT_CHARS = 7000


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON schema
    fn: Callable[..., Any]
    personas: Tuple[str, ...]


def _schema(props: Dict[str, Any], required: Optional[List[str]] = None) -> Dict[str, Any]:
    return {"type": "object", "properties": props, "required": required or [], "additionalProperties": False}


_CROP = {"type": "string", "description": "Crop id: tomato, onion, potato, ginger, garlic or dry_chillies."}
_DISTRICT = {"type": "string", "description": "District id: bengaluru, kolar, chikkaballapur, bengaluru_south or bengaluru_rural."}
_MANDI = {"type": "string", "description": "Mandi id such as kolar_apmc, mulbagal_apmc, bengaluru_apmc (use list_places to see all)."}
_QTY = {"type": "number", "description": "Quantity in quintals (1 tonne = 10 quintals)."}


# ── farmer tools ────────────────────────────────────────────────────────────

def _compact_board(b: Dict[str, Any]) -> Dict[str, Any]:
    if b.get("status") != "OK":
        return {"status": b.get("status"), "reason": b.get("reason")}
    return {
        "status": "OK", "district": b["district"], "crop": b["crop"],
        "price_per_quintal": b["price"]["value"], "price_date": b["price"]["date"], "price_age_days": b["price"]["age_days"],
        "change_pct": b["changes"], "call": b["call"],
        "forecast": [{k: r.get(k) for k in ("horizon", "date", "price", "p05", "p95", "change_pct")} for r in b["forecast"]],
        "reasons": [r.get("code") for r in b.get("reasons", [])],
        "mandis_today": [{"mandi": m["name"], "mandi_kn": m["name_kn"], "mandi_hi": m["name_hi"], "price": m["price"], "min": m["min"], "max": m["max"],
                          "arrivals_tonnes": m["arrivals"], "in_district": m["in_district"]} for m in b["mandis"][:8]],
        "supply": b.get("supply"), "last_year": (b.get("seasonal") or {}).get("last_year"),
        "shelf_life_days": b["shelf"]["days"], "daily_loss_pct": b["shelf"]["daily_loss_pct"],
        "accuracy": b.get("accuracy"),
    }


def _price_board(crop: str, district: str) -> Dict[str, Any]:
    from mandisense_ai.farmer.dashboard import board
    return _compact_board(board(registry.resolve_place(district), str(crop).lower()))


def _district_overview(district: str) -> Dict[str, Any]:
    from mandisense_ai.farmer.dashboard import overview
    o = overview(registry.resolve_place(district))
    return {"district": o["district"], "crops": [{"crop": c["crop"], "price": c["price"], "date": c["date"], "change_7d_pct": c["d7"],
                                                   "call": c["call"].get("type") + (":" + c["call"].get("decision", "") if c["call"].get("decision") else "")}
                                                  for c in o["crops"]]}


def _sell_plan(crop: str, mandi_id: str, quantity_quintals: float = 10) -> Dict[str, Any]:
    from mandisense_ai.farmer.dashboard import sell_plan
    return sell_plan(crop, mandi_id, quantity_quintals)


def _hold_or_sell(crop: str, mandi_id: str, quantity_quintals: float = 10) -> Dict[str, Any]:
    from mandisense_ai.farmer.storage import hold_or_sell
    return hold_or_sell(crop, mandi_id, quantity_quintals)


def _where_to_sell(crop: str, mandi_id: str, quantity_quintals: float = 10) -> Dict[str, Any]:
    from mandisense_ai.farmer.transport import compare_mandis
    r = compare_mandis(crop, origin_mandi_id=registry.resolve_place(mandi_id), quantity_quintals=quantity_quintals)
    if isinstance(r.get("mandis"), list):
        r = {**r, "mandis": r["mandis"][:6]}
    return r


def _seasonal(crop: str, mandi_id: str) -> Dict[str, Any]:
    from mandisense_ai.farmer.seasonal_memory import seasonal_reading
    return seasonal_reading(crop, mandi_id)


def _supply(crop: str, mandi_id: str) -> Dict[str, Any]:
    from mandisense_ai.farmer.supply_signal import supply_reading
    return supply_reading(crop, mandi_id)


def _track_record(crop: str, mandi_id: str) -> Dict[str, Any]:
    from mandisense_ai.farmer.track_record import track_record
    return track_record(crop, mandi_id, None)


def _accuracy() -> Dict[str, Any]:
    from mandisense_ai.farmer import world
    r = world.model_report()
    return {"overall": r.get("overall"), "data": r.get("data"), "honest_note": r.get("honest_note")}


def _crop_planning(mandi_id: str, target_month: int) -> Dict[str, Any]:
    from mandisense_ai.farmer.crop_planning import seasonal_crop_comparison
    return seasonal_crop_comparison(mandi_id, int(target_month))


def _price_on_date(crop: str, mandi_id: str, date: str) -> Dict[str, Any]:
    from mandisense_ai.farmer.price_lookup import price_on_date
    return price_on_date(crop, mandi_id, date)


def _fair_price(crop: str, mandi_id: str, offered_price: float, quantity_quintals: float = 10) -> Dict[str, Any]:
    from mandisense_ai.farmer.fair_price import check_offer
    return check_offer(crop, mandi_id, offered_price, quantity_quintals)


def _mandi_page(mandi_id: str) -> Dict[str, Any]:
    from mandisense_ai.farmer.dashboard import mandi_page
    return mandi_page(mandi_id)


def _list_places() -> Dict[str, Any]:
    return {
        "districts": [{"id": d.id, "name": d.name} for d in registry.DISTRICTS.values()],
        "mandis": [{"id": m.id, "name": m.name, "district": m.district} for m in registry.MANDIS.values()],
        "crops": ["tomato", "onion", "potato", "ginger", "garlic", "dry_chillies"],
    }


# ── trader tools ────────────────────────────────────────────────────────────

def _spreads(crop: str, quantity_quintals: float = 20) -> Dict[str, Any]:
    from mandisense_ai.trader.arbitrage import scan_spreads
    return scan_spreads(crop, quantity_quintals, 8, None)


def _gap_arbitrage(crop: str, quantity_quintals: float = 20, trip_days: int = 3) -> Dict[str, Any]:
    from mandisense_ai.trader.transmission import gap_arbitrage
    return gap_arbitrage(crop, quantity_quintals, trip_days)


def _volatility(crop: str, mandi_id: str) -> Dict[str, Any]:
    from mandisense_ai.trader.volatility import volatility_profile
    r = volatility_profile(crop, mandi_id, 20)
    for bulky in ("timeline", "series", "regime_segments"):
        r.pop(bulky, None)
    return r


def _analogs(crop: str, mandi_id: str, horizon_days: int = 7) -> Dict[str, Any]:
    from mandisense_ai.trader.analogs import find_analogs
    r = find_analogs(crop, mandi_id, 30, int(horizon_days), 10)
    if isinstance(r.get("analogs"), list):
        r["analogs"] = r["analogs"][:5]
    return r


def _scenarios(crop: str, mandi_id: str, horizon_days: int = 5) -> Dict[str, Any]:
    from mandisense_ai.trader.scenarios import run_all
    return run_all(crop, mandi_id, int(horizon_days))


def _forward_price(crop: str, mandi_id: str, horizon_days: int = 7, quantity_quintals: float = 10) -> Dict[str, Any]:
    from mandisense_ai.trader.forward import fair_forward_price
    return fair_forward_price(crop, mandi_id, int(horizon_days), quantity_quintals)


def _transmission() -> Dict[str, Any]:
    from mandisense_ai.trader.transmission import cross_commodity_matrix
    r = cross_commodity_matrix()
    return json.loads(json.dumps(r, default=str)[:MAX_RESULT_CHARS]) if len(json.dumps(r, default=str)) > MAX_RESULT_CHARS else r


def _brief(crop: str, mandi_id: str) -> Dict[str, Any]:
    from mandisense_ai.intelligence.evidence import build_evidence
    from mandisense_ai.intelligence.service import get_intelligence_service
    bundle = build_evidence(crop, mandi_id)
    if not bundle.facts:
        return {"status": "UNAVAILABLE", "reason": f"No evidence for {crop} at {mandi_id}."}
    return get_intelligence_service().build_brief(crop, mandi_id, evidence=bundle).to_dict()


# ── common tools ────────────────────────────────────────────────────────────

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.USub: operator.neg, ast.Mod: operator.mod}


_MAX_EXPR = 120
_MAX_OPERAND = 1e12
_MAX_EXPONENT = 8


def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        if abs(node.value) > _MAX_OPERAND:
            raise ValueError("number too large")
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > _MAX_EXPONENT:
            raise ValueError("exponent too large")  # 9**9**9**9 must not freeze the server
        value = _OPS[type(node.op)](left, right)
        if abs(value) > _MAX_OPERAND * 1e6:
            raise ValueError("result too large")
        return value
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("unsupported expression")


def _calculator(expression: str) -> Dict[str, Any]:
    try:
        text = str(expression).replace("×", "*").replace("÷", "/").replace(",", "")
        if len(text) > _MAX_EXPR:
            raise ValueError("expression too long")
        value = _eval(ast.parse(text, mode="eval").body)
        return {"expression": expression, "result": round(float(value), 4)}
    except Exception:
        return {"expression": expression, "error": "could not evaluate"}


def _web_search(query: str) -> Dict[str, Any]:
    return web.search(query, 5)


def _fetch_url(url: str) -> Dict[str, Any]:
    return web.fetch(url)


def _weather(place: str, days: int = 3) -> Dict[str, Any]:
    entry = registry.MANDIS.get(registry.resolve_place(place)) or registry.DISTRICTS.get(registry.resolve_place(place))
    if entry is not None:
        return web.weather(entry.name.split(" (")[0], entry.lat, entry.lon, int(days))
    return web.weather(place, None, None, int(days))


F, T, BOTH = ("farmer",), ("trader",), ("farmer", "trader")

TOOLS: List[Tool] = [
    Tool("get_price_board", "Today's recorded price for a crop in a district, 7/30-day change, the forecast range, whether the record has earned a sell/hold call, prices at each mandi, supply and last-year comparison. Use for 'what is my crop worth'.",
         _schema({"crop": _CROP, "district": _DISTRICT}, ["crop", "district"]), _price_board, BOTH),
    Tool("get_district_overview", "Every crop's latest price and call in one district.", _schema({"district": _DISTRICT}, ["district"]), _district_overview, BOTH),
    Tool("get_sell_plan", "One answer for one load: sell here today, take it to a better mandi, or wait, with rupee totals net of transport and spoilage.",
         _schema({"crop": _CROP, "mandi_id": _MANDI, "quantity_quintals": _QTY}, ["crop", "mandi_id"]), _sell_plan, F),
    Tool("get_hold_or_sell", "Whether to hold or sell now, after spoilage, for a crop at a mandi.",
         _schema({"crop": _CROP, "mandi_id": _MANDI, "quantity_quintals": _QTY}, ["crop", "mandi_id"]), _hold_or_sell, F),
    Tool("get_where_to_sell", "Compare nearby mandis for a crop after transport cost.",
         _schema({"crop": _CROP, "mandi_id": _MANDI, "quantity_quintals": _QTY}, ["crop", "mandi_id"]), _where_to_sell, F),
    Tool("get_seasonal_memory", "This time last year: how today's price compares with the same season before.",
         _schema({"crop": _CROP, "mandi_id": _MANDI}, ["crop", "mandi_id"]), _seasonal, BOTH),
    Tool("get_supply_signal", "Whether arrivals at the mandi are unusually high or low (a supply glut warning).",
         _schema({"crop": _CROP, "mandi_id": _MANDI}, ["crop", "mandi_id"]), _supply, BOTH),
    Tool("get_track_record", "How often the forecasts for this crop at this mandi have been right.",
         _schema({"crop": _CROP, "mandi_id": _MANDI}, ["crop", "mandi_id"]), _track_record, F),
    Tool("get_accuracy", "Overall measured accuracy of the price forecasts.", _schema({}), _accuracy, BOTH),
    Tool("get_crop_planning", "Which crops have paid best in a given month at a mandi (what to plant).",
         _schema({"mandi_id": _MANDI, "target_month": {"type": "integer", "minimum": 1, "maximum": 12}}, ["mandi_id", "target_month"]), _crop_planning, F),
    Tool("get_price_on_date", "The recorded price for a crop at a mandi on a past date (YYYY-MM-DD).",
         _schema({"crop": _CROP, "mandi_id": _MANDI, "date": {"type": "string"}}, ["crop", "mandi_id", "date"]), _price_on_date, BOTH),
    Tool("check_fair_price", "Is a price a buyer offers fair, against recorded prices?",
         _schema({"crop": _CROP, "mandi_id": _MANDI, "offered_price": {"type": "number"}, "quantity_quintals": _QTY}, ["crop", "mandi_id", "offered_price"]), _fair_price, F),
    Tool("get_mandi_page", "Every crop's latest price at one mandi.", _schema({"mandi_id": _MANDI}, ["mandi_id"]), _mandi_page, BOTH),
    Tool("list_places", "The districts, mandis and crops the records cover, with their ids.", _schema({}), _list_places, BOTH),

    Tool("scan_spreads", "Trader: mandi-to-mandi spreads for a crop, net of transport and expected to still be there on arrival.",
         _schema({"crop": _CROP, "quantity_quintals": _QTY}, ["crop"]), _spreads, T),
    Tool("gap_arbitrage", "Trader: same-crop district price gaps projected over a trip length, net of transport.",
         _schema({"crop": _CROP, "quantity_quintals": _QTY, "trip_days": {"type": "integer", "minimum": 1, "maximum": 14}}, ["crop"]), _gap_arbitrage, T),
    Tool("get_volatility", "Trader: current volatility regime (calm/normal/turbulent) and its percentile against the series' own history.",
         _schema({"crop": _CROP, "mandi_id": _MANDI}, ["crop", "mandi_id"]), _volatility, T),
    Tool("get_analogs", "Trader: historical periods that looked like today and what happened next.",
         _schema({"crop": _CROP, "mandi_id": _MANDI, "horizon_days": {"type": "integer", "minimum": 1, "maximum": 30}}, ["crop", "mandi_id"]), _analogs, T),
    Tool("run_scenarios", "Trader: what happened historically after conditions like arrivals surges or volatility spikes.",
         _schema({"crop": _CROP, "mandi_id": _MANDI, "horizon_days": {"type": "integer", "minimum": 1, "maximum": 30}}, ["crop", "mandi_id"]), _scenarios, T),
    Tool("get_forward_price", "Trader: forward price range for a horizon from the calibrated forecast.",
         _schema({"crop": _CROP, "mandi_id": _MANDI, "horizon_days": {"type": "integer", "minimum": 1, "maximum": 14}, "quantity_quintals": _QTY}, ["crop", "mandi_id"]), _forward_price, T),
    Tool("get_transmission_matrix", "Trader: the tested cross-commodity transmission links and their evidence tiers.", _schema({}), _transmission, T),
    Tool("get_decision_brief", "Trader: the evidence-checked decision brief for one crop at one mandi.",
         _schema({"crop": _CROP, "mandi_id": _MANDI}, ["crop", "mandi_id"]), _brief, T),

    Tool("web_search", "Search the live web. Use for anything the mandi records do not cover: government schemes, MSP, fertiliser, pests and disease, news, policy, export rules, farming practice, or when a records tool returns no data.",
         _schema({"query": {"type": "string", "description": "A specific search query."}}, ["query"]), _web_search, BOTH),
    Tool("fetch_url", "Read the text of a public web page (use after web_search to get details).",
         _schema({"url": {"type": "string"}}, ["url"]), _fetch_url, BOTH),
    Tool("get_weather", "Weather forecast for a place in India: temperature and rain for the next days.",
         _schema({"place": {"type": "string"}, "days": {"type": "integer", "minimum": 1, "maximum": 7}}, ["place"]), _weather, BOTH),
    Tool("calculator", "Exact arithmetic (rupees, quintals, percentages). Use instead of computing numbers yourself.",
         _schema({"expression": {"type": "string"}}, ["expression"]), _calculator, BOTH),
]

_BY_NAME = {t.name: t for t in TOOLS}


def tools_for(persona: str) -> List[Tool]:
    return [t for t in TOOLS if persona in t.personas]


def run_tool(name: str, args: Dict[str, Any], persona: str) -> Dict[str, Any]:
    """Run a tool the persona is allowed, returning a dict (never raising)."""
    tool = _BY_NAME.get(name)
    if tool is None or persona not in tool.personas:
        return {"error": f"unknown tool: {name}"}
    try:
        clean = {k: v for k, v in (args or {}).items() if k in tool.parameters["properties"]}
        result = tool.fn(**clean)
    except TypeError as exc:
        return {"error": f"bad arguments for {name}: {exc}"}
    except Exception as exc:
        logger.warning("tool %s failed: %s", name, exc)
        return {"error": f"{name} failed: {type(exc).__name__}"}
    if not isinstance(result, dict):
        result = {"result": result}
    text = json.dumps(result, default=str, ensure_ascii=False)
    if len(text) > MAX_RESULT_CHARS:
        result = {"truncated": True, "data": text[:MAX_RESULT_CHARS]}
    return result
