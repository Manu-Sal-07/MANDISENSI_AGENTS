"""
Screenshots of the insight features for the report and the deck (headless Chrome over the DevTools protocol).

    python report/capture_insight_ui.py [--web http://localhost:3000]

Needs the API (port 8000) and the web app (port 3000) running with the current code. Writes report/figures/ins_*.png.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import websocket

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "report" / "figures"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9344


class Browser:
    def __init__(self, width: int, height: int, mobile: bool):
        self.profile = tempfile.mkdtemp(prefix="cdp_")
        self.proc = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", f"--remote-debugging-port={PORT}", f"--user-data-dir={self.profile}",
                                      "--hide-scrollbars", f"--window-size={width},{height}", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        tabs = None
        for _ in range(60):
            try:
                tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
                break
            except Exception:
                time.sleep(0.5)
        self.ws = websocket.create_connection([t for t in tabs if t["type"] == "page"][0]["webSocketDebuggerUrl"], timeout=90)
        self.n = 0
        self.call("Page.enable")
        self.call("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=2 if mobile else 1.5, mobile=mobile)

    def call(self, method, **params):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.n:
                return msg.get("result", msg)

    def js(self, expr):
        return self.call("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True).get("result", {}).get("value")

    def go(self, url, wait=7):
        self.call("Page.navigate", url=url)
        time.sleep(wait)

    def shot(self, path, clip=None):
        p = {"format": "png"}
        if clip:
            p["clip"] = {**clip, "scale": 1}
        Path(path).write_bytes(base64.b64decode(self.call("Page.captureScreenshot", **p)["data"]))

    def rect(self, expr):
        return self.js(f"(()=>{{const e={expr};if(!e)return null;const r=e.getBoundingClientRect();return {{x:r.x+scrollX,y:r.y+scrollY,width:r.width,height:r.height}}}})()")

    def click_text(self, text, tag="button,a,[role=button]"):
        return self.js("""(()=>{const t=%s;const e=[...document.querySelectorAll(%s)].find(x=>x.innerText&&x.innerText.includes(t));if(!e)return 'none';e.click();return 'clicked'})()"""
                       % (json.dumps(text), json.dumps(tag)))

    def close(self):
        self.proc.kill()


def farmer(web: str) -> None:
    b = Browser(480, 2600, True)
    try:
        b.go(web + "/tools", 3)
        b.js("localStorage.setItem('mandisense-farm-lang','en'); localStorage.setItem('mandisense-best-place-v1', JSON.stringify({district:'kolar',vehicle:'tempo',alpha:0.1}))")
        b.go(web + "/tools", 7)
        print("tool:", b.click_text("Best Place"))
        time.sleep(8)
        hide = """(()=>{document.querySelectorAll('nextjs-portal').forEach(e=>e.remove());
          [...document.querySelectorAll('body *')].forEach(e=>{const cs=getComputedStyle(e);
            if(cs.position==='fixed'&&!e.innerText.includes('Best Place')&&!e.innerText.includes('Sell at')) e.style.display='none';})})()"""
        for label in ["Why this mandi?", "What if my costs", "Has this advice worked?"]:
            print(label, b.click_text(label))
            time.sleep(4)
        b.js(hide)

        def panel(name, finder):
            b.js("(()=>{const e=%s;if(e)e.scrollIntoView({block:'center'})})()" % finder)
            time.sleep(1.2)
            r = b.js("(()=>{const e=%s;if(!e)return null;const r=e.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height}})()" % finder)
            if r:
                b.shot(FIG / f"ins_farmer_{name}.png", r)
                print("saved", name, round(r["height"]))

        panel("advice", "[...document.querySelectorAll('p')].find(x=>x.innerText.trim().toLowerCase()==='sell at')?.closest('div.rounded-3xl')")
        for label, name in [("Why this mandi?", "why"), ("What if my costs", "whatif"), ("Has this advice worked?", "score")]:
            panel(name, "[...document.querySelectorAll('button')].find(x=>x.innerText.includes(%s))?.closest('div.rounded-2xl')" % json.dumps(label))
    finally:
        b.close()


def trader(web: str) -> None:
    b = Browser(1360, 1500, False)
    try:
        for slug in ("reporting-value", "crowd-simulator"):
            b.go(f"{web}/trader-tools/{slug}", 9)
            b.shot(FIG / f"ins_trader_{slug}.png")
            print("saved", slug)
    finally:
        b.close()


def telegram_mock() -> None:
    """The digest text exactly as the bot sends it, set in a chat bubble (a rendering, not a Telegram screenshot)."""
    sys.path.insert(0, str(ROOT))
    from datetime import date

    from mandisense_ai.notify import digest

    text = digest.build_digest("kolar", ["tomato", "potato"], "en", today=date(2026, 10, 29))
    body = html.escape(text).replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>").replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>").replace("\n", "<br>")
    page = f"""<html><body style="margin:0;background:#cfe3f1;font-family:Segoe UI,Roboto,sans-serif">
    <div style="width:520px;padding:18px 16px 24px 16px">
      <div style="background:#2a8fd0;color:#fff;border-radius:12px 12px 0 0;padding:10px 14px;font-weight:600">MandiSense AI · bot</div>
      <div style="background:#e7f0f7;padding:16px 12px 18px 12px;border-radius:0 0 12px 12px">
        <div style="background:#fff;border-radius:14px 14px 14px 4px;padding:12px 14px;font-size:15px;line-height:1.38;color:#111;box-shadow:0 1px 2px rgba(0,0,0,.15)">{body}
        <div style="text-align:right;font-size:11px;color:#8a98a5;margin-top:6px">07:00</div></div></div></div></body></html>"""
    f = Path(tempfile.gettempdir()) / "digest_mock.html"
    f.write_text(page, encoding="utf-8")
    b = Browser(560, 900, False)
    try:
        b.go(f.as_uri(), 2)
        r = b.rect("document.body.firstElementChild")
        b.shot(FIG / "ins_digest.png", r)
        print("saved digest")
    finally:
        b.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--web", default="http://localhost:3000")
    ap.add_argument("--only", choices=["farmer", "trader", "digest"])
    a = ap.parse_args()
    if a.only in (None, "digest"):
        telegram_mock()
    if a.only in (None, "farmer"):
        farmer(a.web)
    if a.only in (None, "trader"):
        trader(a.web)
