"""
Screenshots of the running system for the thesis (headless Chrome over the DevTools protocol).

    python report/capture_system.py [--web http://localhost:3000] [--api http://localhost:8000] [--only farmer|trader|other]

Needs the API and the web app running with current code and the data loaded. Writes report/figures/sys_*.png (full-page captures, capped in height).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capture_insight_ui as U  # noqa: E402

FIG = U.FIG
MAXH = 3400

FARMER_PAGES = [("home", "/"), ("prices", "/prices"), ("mandi", "/mandi/kolar_apmc"), ("sellplan", "/sell-plan"), ("mymoney", "/my-money"), ("tools", "/tools"),
                ("accuracy", "/accuracy"), ("evidence", "/evidence")]
FARMER_TOOLS = [("besplace", "Best Place"), ("fairprice", "Fair Price"), ("harvest", "My Harvest"), ("holdorsell", "Hold or Sell"), ("lastyear", "This Time Last Year"),
                ("wheretosell", "Where to Sell"), ("supply", "Supply Signal"), ("record", "Did We Get It Right"), ("truck", "Truck Sharing"), ("plant", "What to Plant"),
                ("alerts", "Price Alerts")]
TRADER_PAGES = [("trader", "/trader"), ("tradertools", "/trader-tools"), ("spreads", "/trader-tools/spreads"), ("mcdesk", "/trader-tools/market-choice"),
                ("shock", "/trader-tools/shock-desk"), ("gap", "/trader-tools/gap-arbitrage"), ("transmission", "/trader-tools/transmission"), ("volatility", "/trader-tools/volatility"),
                ("scenarios", "/trader-tools/scenarios"), ("analogs", "/trader-tools/analogs"), ("forward", "/trader-tools/forward-price"), ("positions", "/trader-tools/positions"),
                ("floormon", "/trader-tools/floor-monitor"), ("audit", "/trader-tools/forecast-audit"), ("council", "/trader-tools/agent-council"),
                ("explorer", "/market-explorer"), ("aibrief", "/ai-brief"), ("lab", "/intelligence-lab"), ("terminal", "/terminal")]


HIDE = """(()=>{document.querySelectorAll('nextjs-portal').forEach(e=>e.remove());
  [...document.querySelectorAll('body *')].forEach(e=>{const cs=getComputedStyle(e);
    if(cs.position==='fixed'){const t=(e.innerText||'');
      if(t.includes('Ask MandiSense') || (t.includes('Home') && t.includes('Prices') && t.includes('Tools') && t.length<80)) e.style.display='none';}})})()"""


def full_shot(b: U.Browser, path: Path, y0: int = 0, h: int = MAXH) -> tuple[int, int]:
    b.js(HIDE)
    m = b.call("Page.getLayoutMetrics")
    cs = m.get("cssContentSize") or m.get("contentSize")
    w = int(cs["width"])
    h = int(min(cs["height"] - y0, h))
    r = b.call("Page.captureScreenshot", format="png", captureBeyondViewport=True, clip={"x": 0, "y": y0, "width": w, "height": max(h, 100), "scale": 1})
    path.write_bytes(__import__("base64").b64decode(r["data"]))
    return w, h


def sheet_shot(b: U.Browser, label: str, path: Path) -> bool:
    b.js(HIDE)
    rect = b.js("""(()=>{const t=%s;const c=[...document.querySelectorAll('body *')].filter(e=>getComputedStyle(e).position==='fixed'&&(e.innerText||'').includes(t));
      if(!c.length)return null;const e=c[c.length-1];const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height}})()""" % json.dumps(label))
    if not rect or rect["height"] < 200:
        return False
    b.shot(path, rect)
    return True


def farmer(web: str) -> None:
    b = U.Browser(480, 1000, True)
    try:
        b.go(web + "/", 3)
        b.js("localStorage.setItem('mandisense-farm-lang','en'); localStorage.setItem('mandisense-best-place-v1', JSON.stringify({district:'kolar',vehicle:'tempo',alpha:0.1}))")
        for name, url in FARMER_PAGES:
            b.go(web + url, 8)
            print(name, full_shot(b, FIG / f"sys_farmer_{name}.png", 0, 1750))
            if name in ("home", "prices", "evidence"):
                print(name + "_b", full_shot(b, FIG / f"sys_farmer_{name}_b.png", 1750, 1750))
        b.call("Emulation.setDeviceMetricsOverride", width=480, height=2000, deviceScaleFactor=2, mobile=True)
        for name, label in FARMER_TOOLS:
            b.go(web + "/tools", 6)
            res = b.click_text(label)
            time.sleep(8)
            ok = sheet_shot(b, label, FIG / f"sys_tool_{name}.png") if res == "clicked" else False
            print("tool", name, res, ok)
    finally:
        b.close()


def trader(web: str) -> None:
    b = U.Browser(1360, 1000, False)
    try:
        for name, url in TRADER_PAGES:
            b.go(web + url, 10)
            print(name, full_shot(b, FIG / f"sys_trader_{name}.png", 3000))
    finally:
        b.close()


def other(api: str) -> None:
    b = U.Browser(1360, 1000, False)
    try:
        b.go(api + "/docs", 6)
        print("docs", full_shot(b, FIG / "sys_api_docs.png", 2200))
    finally:
        b.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--web", default="http://localhost:3000")
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--only", choices=["farmer", "trader", "other"])
    a = ap.parse_args()
    if a.only in (None, "farmer"):
        farmer(a.web)
    if a.only in (None, "trader"):
        trader(a.web)
    if a.only in (None, "other"):
        other(a.api)
