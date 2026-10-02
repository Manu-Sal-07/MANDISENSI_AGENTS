"""
Live web access for the chatbots: search, page fetch and weather.

Used whenever the mandi records cannot answer (government schemes, fertiliser,
pests, news, anything outside prices). Keyless: web search uses DuckDuckGo via
the `ddgs` package with a Wikipedia fallback, weather uses Open-Meteo.

Because the model chooses the URL it fetches, `fetch` refuses anything that is
not a public http(s) address (no localhost, private ranges or link-local), and
re-checks every redirect hop.
"""

from __future__ import annotations

import ipaddress
import socket
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

from mandisense_ai.utils.logger import get_logger

logger = get_logger(__name__)

_UA = "Mozilla/5.0 (compatible; MandiSenseBot/1.0; +https://github.com/Manu-Sal-07/MANDISENSI_AGENTS)"
_CACHE: Dict[str, Any] = {}
_TTL_SECONDS = 600
_MAX_BYTES = 1_500_000


def _cached(key: str):
    hit = _CACHE.get(key)
    if hit and time.time() - hit[0] < _TTL_SECONDS:
        return hit[1]
    return None


def _store(key: str, value):
    if len(_CACHE) > 200:
        _CACHE.clear()
    _CACHE[key] = (time.time(), value)
    return value


def is_public_url(url: str) -> bool:
    """True only for http(s) URLs whose host resolves to public addresses."""
    try:
        parts = urlparse(url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            return False
        infos = socket.getaddrinfo(parts.hostname, parts.port or (443 if parts.scheme == "https" else 80))
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
                return False
        return True
    except Exception:
        return False


def _wikipedia(query: str, n: int) -> List[Dict[str, str]]:
    r = requests.get(
        "https://en.wikipedia.org/w/api.php",
        params={"action": "query", "list": "search", "srsearch": query, "srlimit": n, "format": "json"},
        headers={"User-Agent": _UA}, timeout=10,
    )
    r.raise_for_status()
    out = []
    for hit in r.json().get("query", {}).get("search", []):
        title = hit["title"]
        snippet = hit.get("snippet", "").replace('<span class="searchmatch">', "").replace("</span>", "")
        out.append({"title": title, "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}", "snippet": snippet})
    return out


def search(query: str, max_results: int = 5) -> Dict[str, Any]:
    """Web search. Returns {"query", "results": [{title, url, snippet}], "engine"}."""
    query = (query or "").strip()[:300]
    if not query:
        return {"query": query, "results": [], "engine": None, "error": "empty query"}
    key = f"s:{query}:{max_results}"
    cached = _cached(key)
    if cached:
        return cached

    results: List[Dict[str, str]] = []
    engine = None
    try:
        from ddgs import DDGS

        for r in DDGS(timeout=8).text(query, region="in-en", max_results=max_results):
            results.append({"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")})
        engine = "duckduckgo"
    except Exception as exc:  # network, rate limit, package missing
        logger.warning("ddgs search failed (%s); trying Wikipedia", exc)
    if not results:
        try:
            results = _wikipedia(query, max_results)
            engine = "wikipedia"
        except Exception as exc:
            logger.warning("wikipedia search failed: %s", exc)
            return {"query": query, "results": [], "engine": None, "error": "web search unavailable"}
    return _store(key, {"query": query, "results": results[:max_results], "engine": engine})


def _html_to_text(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "form", "aside", "svg"]):
        tag.decompose()
    main = soup.find("article") or soup.find("main") or soup.body or soup
    lines = [ln.strip() for ln in main.get_text("\n").splitlines()]
    return "\n".join(ln for ln in lines if len(ln) > 2)


def fetch(url: str, max_chars: int = 4000) -> Dict[str, Any]:
    """Fetch a public web page and return its readable text."""
    key = f"f:{url}:{max_chars}"
    cached = _cached(key)
    if cached:
        return cached
    current = url
    try:
        for _ in range(4):  # follow a few redirects, vetting each hop
            if not is_public_url(current):
                return {"url": url, "error": "blocked: not a public http(s) address"}
            resp = requests.get(current, headers={"User-Agent": _UA}, timeout=10, stream=True, allow_redirects=False)
            if resp.is_redirect and resp.headers.get("location"):
                current = requests.compat.urljoin(current, resp.headers["location"])
                continue
            ctype = resp.headers.get("content-type", "")
            if resp.status_code >= 400:
                return {"url": url, "error": f"HTTP {resp.status_code}"}
            if "html" not in ctype and "text" not in ctype and "json" not in ctype:
                return {"url": url, "error": f"unsupported content type: {ctype or 'unknown'}"}
            raw = b""
            for chunk in resp.iter_content(65536):
                raw += chunk
                if len(raw) > _MAX_BYTES:
                    break
            text = raw.decode(resp.encoding or "utf-8", errors="replace")
            body = _html_to_text(text) if "html" in ctype else text
            return _store(key, {"url": current, "text": body[:max_chars], "truncated": len(body) > max_chars})
        return {"url": url, "error": "too many redirects"}
    except Exception as exc:
        return {"url": url, "error": f"fetch failed: {type(exc).__name__}"}


_WEATHER_CODES = {
    0: "clear", 1: "mostly clear", 2: "partly cloudy", 3: "overcast", 45: "fog", 48: "fog",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle", 61: "light rain", 63: "rain", 65: "heavy rain",
    80: "rain showers", 81: "rain showers", 82: "violent rain showers", 95: "thunderstorm", 96: "thunderstorm with hail",
}


def weather(place: str, lat: Optional[float] = None, lon: Optional[float] = None, days: int = 3) -> Dict[str, Any]:
    """Forecast for a place (Open-Meteo): max/min temperature and rain for the next days."""
    key = f"w:{place}:{lat}:{lon}:{days}"
    cached = _cached(key)
    if cached:
        return cached
    try:
        name = place
        if lat is None or lon is None:
            geo = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                               params={"name": place, "count": 1, "country_code": "IN"}, timeout=10).json()
            hit = (geo.get("results") or [None])[0]
            if not hit:
                return {"place": place, "error": "place not found"}
            lat, lon, name = hit["latitude"], hit["longitude"], hit.get("name", place)
        data = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": lat, "longitude": lon, "timezone": "Asia/Kolkata", "forecast_days": days,
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode"},
            timeout=10,
        ).json()["daily"]
        rows = [
            {"date": data["time"][i], "max_c": data["temperature_2m_max"][i], "min_c": data["temperature_2m_min"][i],
             "rain_mm": data["precipitation_sum"][i], "summary": _WEATHER_CODES.get(data["weathercode"][i], "mixed")}
            for i in range(len(data["time"]))
        ]
        return _store(key, {"place": name, "days": rows, "source": "Open-Meteo"})
    except Exception as exc:
        return {"place": place, "error": f"weather unavailable: {type(exc).__name__}"}
