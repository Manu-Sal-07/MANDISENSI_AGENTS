"""
Re-capture the farmer tool sheets at one fixed phone viewport (480x1000 CSS px, 2x), so every sheet has the same scale.

    python report/capture_tools.py [--web http://localhost:3000]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import capture_insight_ui as U  # noqa: E402
from capture_system import FARMER_TOOLS, FIG, HIDE  # noqa: E402


def main(web: str) -> None:
    b = U.Browser(480, 1000, True)
    try:
        b.go(web + "/", 3)
        b.js("localStorage.setItem('mandisense-farm-lang','en'); localStorage.setItem('mandisense-best-place-v1', JSON.stringify({district:'kolar',vehicle:'tempo',alpha:0.1}))")
        for name, label in FARMER_TOOLS:
            b.go(web + "/tools", 6)
            res = b.click_text(label)
            time.sleep(8)
            b.js(HIDE)
            b.shot(FIG / f"sys_tool_{name}.png")
            print("tool", name, res)
    finally:
        b.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--web", default="http://localhost:3000")
    main(ap.parse_args().web)
