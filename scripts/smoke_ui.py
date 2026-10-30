"""
Smoke-test the running application: every API endpoint the pages depend on, and every page rendered in headless Chrome.

    python scripts/smoke_ui.py                          # both servers on their default ports
    python scripts/smoke_ui.py --web http://localhost:3000 --api http://localhost:8000
    python scripts/smoke_ui.py --only trader-tools      # only routes containing this text
    python scripts/smoke_ui.py --no-pages               # API checks only (no browser needed)

A page passes if it renders more than a handful of words, shows no application-error screen and writes no error to the browser
console. An API check passes if the endpoint answers 200 and, where it reports one, `status` is not an error. Needs only Chrome
or Edge installed (no browser driver to download), so it runs on any developer machine and in CI. Exit code 1 if anything fails.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from typing import List, Optional, Tuple

PAGES = [
    "", "sell-plan", "my-money", "tools", "prices", "accuracy", "evidence", "ai-brief",
    "trader", "trader-tools", "market-explorer", "intelligence-lab", "terminal", "mandi/kolar_apmc",
    "trader-tools/spreads", "trader-tools/market-choice", "trader-tools/shock-desk", "trader-tools/gap-arbitrage",
    "trader-tools/transmission", "trader-tools/volatility", "trader-tools/scenarios", "trader-tools/analogs",
    "trader-tools/forward-price", "trader-tools/positions", "trader-tools/floor-monitor", "trader-tools/forecast-audit",
    "trader-tools/agent-council", "trader-tools/reporting-value", "trader-tools/crowd-simulator",
]
ENDPOINTS = [
    "/v1/health", "/v1/farmer/mandis", "/v1/market-choice/crops", "/v1/market-choice/recommend/tomato?district=kolar&quantity_quintals=20",
    "/v1/market-choice/matrix/tomato?district=kolar", "/v1/market-choice/evidence",
    "/v1/market-choice/breakdown/tomato?district=kolar", "/v1/market-choice/simulate/tomato?district=kolar&transport_per_q_km=1.4",
    "/v1/market-choice/crowd/tomato?district=kolar&farmers=200", "/v1/market-choice/reporting-value/tomato", "/v1/market-choice/track-record/tomato", "/v1/shock/radar?audience=farmer&crop=tomato&district=kolar",
    "/v1/shock/radar?audience=trader", "/v1/shock/study", "/v1/council/tomato/kolar_apmc", "/v1/council/evaluation",
    "/v1/trader/spreads/tomato", "/v1/trader/transmission/matrix", "/v1/trader/volatility/tomato/kolar_apmc",
    "/v1/trader/analogs/tomato/kolar_apmc", "/v1/trader/scenarios/tomato/kolar_apmc", "/v1/trader/forward-price/tomato/kolar_apmc?horizon_days=3",
    "/v1/market-data/markets", "/v1/market-data/summary/tomato/kolar_apmc", "/v1/cognition/available", "/v1/cognition/state/tomato/kolar_apmc",
    "/v1/forecast/status", "/v1/spillover/status", "/v1/intelligence/status", "/v1/chat/status",
]
ERROR_PATTERN = re.compile(r"\[ERROR\]|Uncaught|Unhandled|Application error|Failed to fetch|TypeError|ReferenceError")
MIN_WORDS = 40


def find_chrome() -> Optional[str]:
    for env in ("CHROME_PATH", "CHROME_BIN"):
        if os.environ.get(env) and os.path.exists(os.environ[env]):
            return os.environ[env]
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge"):
        found = shutil.which(name)
        if found:
            return found
    for path in (r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                 r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"):
        if os.path.exists(path):
            return path
    return None


def check_endpoint(base: str, path: str) -> Tuple[bool, str]:
    try:
        with urllib.request.urlopen(base + path, timeout=90) as r:
            body = r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"
    try:
        data = json.loads(body)
    except ValueError:
        return False, "not JSON"
    status = data.get("status") if isinstance(data, dict) else None
    if isinstance(status, str) and status.lower() in {"error", "failed"}:
        return False, f"status={status}: {str(data.get('message') or data.get('reason') or '')[:80]}"
    return True, f"status={status}" if status else "ok"


def check_page(chrome: str, base: str, route: str, profile: str) -> Tuple[bool, str]:
    cmd = [chrome, "--headless=new", "--disable-gpu", "--no-sandbox", f"--user-data-dir={profile}", "--virtual-time-budget=25000",
           "--enable-logging=stderr", "--v=0", "--dump-dom", f"{base}/{route}"]
    try:
        run = subprocess.run(cmd, capture_output=True, timeout=150)
    except subprocess.TimeoutExpired:
        return False, "timed out"
    dom, err = run.stdout.decode("utf-8", "replace"), run.stderr.decode("utf-8", "replace")
    body = re.sub(r"<(script|style|noscript)[\s\S]*?</\1>", " ", dom[dom.find("<body"):] if "<body" in dom else dom)
    text = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))).strip()
    words = len(text.split())
    errors = sorted({re.sub(r"\[\d{4}-[^\]]*\]\s*", "", line.split("CONSOLE:")[-1])[:120] for line in err.splitlines()
                     if "CONSOLE" in line and ERROR_PATTERN.search(line)})
    if words < MIN_WORDS:
        return False, f"only {words} words rendered"
    if re.search(r"Application error|This page could not be found", text):
        return False, "error screen"
    if errors:
        return False, f"console: {errors[0]}"
    return True, f"{words} words"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--web", default="http://localhost:3000")
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--only", default="")
    ap.add_argument("--no-pages", action="store_true")
    ap.add_argument("--no-api", action="store_true")
    a = ap.parse_args()

    failures: List[str] = []
    if not a.no_api:
        print(f"API  {a.api}")
        for path in [e for e in ENDPOINTS if a.only in e]:
            ok, note = check_endpoint(a.api, path)
            print(f"  {'PASS' if ok else 'FAIL'}  {path}  {note}")
            if not ok:
                failures.append(f"api {path}: {note}")
    if not a.no_pages:
        chrome = find_chrome()
        if chrome is None:
            print("No Chrome/Edge found (set CHROME_PATH); skipping pages.")
            failures.append("no browser available")
        else:
            print(f"WEB  {a.web}  ({os.path.basename(chrome)})")
            with tempfile.TemporaryDirectory() as profile:
                for route in [p for p in PAGES if a.only in p]:
                    ok, note = check_page(chrome, a.web, route, profile)
                    print(f"  {'PASS' if ok else 'FAIL'}  /{route}  {note}")
                    if not ok:
                        failures.append(f"page /{route}: {note}")
    print(f"\n{'ALL PASSED' if not failures else str(len(failures)) + ' FAILED'}")
    for f in failures:
        print("  -", f)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
