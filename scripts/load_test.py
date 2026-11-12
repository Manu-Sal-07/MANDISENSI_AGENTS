"""
Measure how the API behaves under concurrent load, so scale claims are numbers and not guesses.

    python scripts/load_test.py                                  # local server on :8000
    python scripts/load_test.py --api https://mandisense-api.onrender.com --levels 1 5 10 25 --requests 100

Each level sends `--requests` requests from `level` concurrent clients, drawn round-robin from a realistic mix of the endpoints a farmer and
a trader use (recommendation, breakdown, spreads, forecast status, health). It first sends one warm-up pass so a cold start or the first
heavy computation is not counted as steady-state latency (the warm-up is reported separately). Reports throughput, p50 / p95 / max latency
and the error rate per level. Be considerate with a free-tier host: the defaults are small.
"""

from __future__ import annotations

import argparse
import asyncio
import statistics
import time
from typing import List, Tuple

import httpx

MIX = [
    "/v1/market-choice/recommend/tomato?district=kolar&quantity_quintals=20",
    "/v1/market-choice/breakdown/tomato?district=kolar",
    "/v1/market-choice/recommend/onion?district=kolar&quantity_quintals=10",
    "/v1/trader/spreads/tomato",
    "/v1/forecast/status",
    "/v1/health",
]


def pct(values: List[float], q: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(q * (len(ordered) - 1))))]


async def one(client: httpx.AsyncClient, base: str, path: str) -> Tuple[bool, float, int]:
    start = time.perf_counter()
    try:
        r = await client.get(base + path)
        return r.status_code == 200, time.perf_counter() - start, r.status_code
    except Exception:
        return False, time.perf_counter() - start, 0


async def run_level(base: str, level: int, total: int) -> dict:
    sem = asyncio.Semaphore(level)
    results: List[Tuple[bool, float, int]] = []
    async with httpx.AsyncClient(timeout=120) as client:
        async def task(i: int) -> None:
            async with sem:
                results.append(await one(client, base, MIX[i % len(MIX)]))

        t0 = time.perf_counter()
        await asyncio.gather(*(task(i) for i in range(total)))
        wall = time.perf_counter() - t0
    lat = [r[1] for r in results]
    codes = sorted({r[2] for r in results})
    return {
        "level": level, "requests": total, "rps": total / wall, "p50": pct(lat, 0.5), "p95": pct(lat, 0.95), "max": max(lat),
        "errors": sum(1 for r in results if not r[0]), "codes": codes,
    }


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--api", default="http://localhost:8000")
    ap.add_argument("--levels", type=int, nargs="+", default=[1, 5, 10, 25])
    ap.add_argument("--requests", type=int, default=100)
    a = ap.parse_args()

    print(f"Target {a.api}")
    async with httpx.AsyncClient(timeout=180) as client:
        print("Warm-up (one pass over the mix, not counted):")
        for path in MIX:
            ok, secs, code = await one(client, a.api, path)
            print(f"  {code}  {secs:6.2f}s  {path}")
    print(f"\n{'clients':>7} {'reqs':>5} {'req/s':>7} {'p50 s':>7} {'p95 s':>7} {'max s':>7} {'errors':>6}  status codes")
    for level in a.levels:
        r = await run_level(a.api, level, a.requests)
        print(f"{r['level']:>7} {r['requests']:>5} {r['rps']:>7.1f} {r['p50']:>7.2f} {r['p95']:>7.2f} {r['max']:>7.2f} {r['errors']:>6}  {r['codes']}")


if __name__ == "__main__":
    asyncio.run(main())
