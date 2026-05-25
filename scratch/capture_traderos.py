import asyncio
import base64
import json
import subprocess
import time
import tempfile
from pathlib import Path

import requests
import websockets


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "ux"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
URL = "http://127.0.0.1:3001/terminal"
PORT = 9331


async def cdp_call(ws, method, params=None, ident=[0]):
    ident[0] += 1
    await ws.send(json.dumps({"id": ident[0], "method": method, "params": params or {}}))
    while True:
        payload = json.loads(await ws.recv())
        if payload.get("id") == ident[0]:
            if "error" in payload:
                raise RuntimeError(payload["error"])
            return payload.get("result", {})


async def capture():
    OUT.mkdir(parents=True, exist_ok=True)
    user_data = Path(tempfile.mkdtemp(prefix="traderos-edge-"))
    proc = subprocess.Popen(
        [
            str(EDGE),
            "--headless=new",
            f"--remote-debugging-port={PORT}",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--hide-scrollbars",
            "--window-size=1600,1000",
            f"--user-data-dir={user_data}",
            URL,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        version = None
        for _ in range(60):
            try:
                version = requests.get(f"http://127.0.0.1:{PORT}/json/version", timeout=1).json()
                break
            except Exception:
                time.sleep(0.25)
        if not version:
            raise RuntimeError("Edge DevTools endpoint did not start")

        targets = requests.get(f"http://127.0.0.1:{PORT}/json", timeout=2).json()
        page = next((target for target in targets if target.get("type") == "page"), None)
        if not page:
            raise RuntimeError("No page target found")

        async with websockets.connect(page["webSocketDebuggerUrl"], max_size=16 * 1024 * 1024) as ws:
            await cdp_call(ws, "Page.enable")
            await cdp_call(ws, "Runtime.enable")
            await cdp_call(ws, "Emulation.setDeviceMetricsOverride", {
                "width": 1600,
                "height": 1000,
                "deviceScaleFactor": 1,
                "mobile": False,
            })
            await cdp_call(ws, "Page.navigate", {"url": URL})
            await asyncio.sleep(7)

            async def shot(name):
                data = await cdp_call(ws, "Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
                (OUT / name).write_bytes(base64.b64decode(data["data"]))

            await shot("traderos-intelligence.png")

            for label, filename in [("QUERY", "traderos-query.png"), ("EVENTS", "traderos-events.png")]:
                await cdp_call(ws, "Runtime.evaluate", {
                    "expression": f"""
                    (() => {{
                      const buttons = [...document.querySelectorAll('button')];
                      const target = buttons.find((button) => button.textContent && button.textContent.trim().includes('{label}'));
                      if (target) target.click();
                      return Boolean(target);
                    }})()
                    """,
                    "awaitPromise": False,
                })
                await asyncio.sleep(1.2)
                await shot(filename)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    asyncio.run(capture())
