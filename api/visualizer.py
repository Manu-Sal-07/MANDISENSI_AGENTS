"""
WebSocket visualiser: streams a traced council run (each specialist agent, external context, the fused forecast) to a client.

The events are produced by `mandisense_ai.forecasting.trace`; this module only paces and sends them, so what the client sees is
exactly what `/v1/trace-run` and the command line report.
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from mandisense_ai.forecasting import trace

logger = logging.getLogger("mandisense_visualizer")

router = APIRouter()

PACE_SECONDS = 0.35        # a short pause between steps so a viewer can follow them


class VisualizerQuery(BaseModel):
    commodity: str
    mandi: str


async def send_event(websocket: WebSocket, step: str, data: Any = None, metadata: Optional[Dict[str, Any]] = None) -> None:
    await websocket.send_json({"step": step, "status": "running", "timestamp": time.time(), "data": data, "metadata": metadata})


@router.websocket("/ws/visualizer")
async def visualizer_websocket(websocket: WebSocket):
    await websocket.accept()
    logger.info("Visualizer WebSocket connected")
    try:
        while True:
            query = await websocket.receive_json()
            commodity, mandi = query.get("commodity", "tomato"), query.get("mandi", "kolar")
            started = time.time()
            events = await asyncio.to_thread(trace.collect, commodity, mandi)
            for event in events:
                await send_event(websocket, event["step"], event["data"])
                await asyncio.sleep(PACE_SECONDS)
            logger.info("Visualizer run complete for %s @ %s in %.1fs", commodity, mandi, time.time() - started)
    except WebSocketDisconnect:
        logger.info("Visualizer WebSocket disconnected")
    except Exception as exc:
        logger.error("Visualizer failure: %s", exc, exc_info=True)
        try:
            await websocket.send_json({"step": "error", "message": str(exc)})
        except Exception:
            pass
