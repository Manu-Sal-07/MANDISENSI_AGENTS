import time
import asyncio
import json
import logging
import uuid
import sys
import os
from typing import Dict, Any, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

# ── Path Configuration ────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
MANDISENSE_AI_PATH = os.path.join(BASE_DIR, "mandisense_ai")
if MANDISENSE_AI_PATH not in sys.path:
    sys.path.append(MANDISENSE_AI_PATH)

# Import original agents
from mandisense_ai.core.agents.seasonality_agent import run_seasonality_agent
from mandisense_ai.core.agents.arrival_volume_agent import run_arrival_volume_agent
from mandisense_ai.core.agents.external_factors_agent import run_external_factors_agent
from mandisense_ai.ensemble.meta_ensemble import run_meta_ensemble

logger = logging.getLogger("mandisense_visualizer")

router = APIRouter()

class VisualizerQuery(BaseModel):
    commodity: str
    mandi: str

async def send_event(websocket: WebSocket, step: str, data: Any = None, metadata: Dict[str, Any] = None):
    """Utility to send a structured event over WebSocket."""
    event = {
        "step": step,
        "timestamp": time.time(),
        "data": data,
        "metadata": metadata or {}
    }
    await websocket.send_json(event)
    # Small delay to allow frontend to animate
    await asyncio.sleep(0.5)

@router.websocket("/ws/visualizer")
async def visualizer_websocket(websocket: WebSocket):
    await websocket.accept()
    logger.info("Visualizer WebSocket connected")
    
    try:
        while True:
            # Wait for query from frontend
            query_data = await websocket.receive_json()
            commodity = query_data.get("commodity", "tomato")
            mandi = query_data.get("mandi", "kolar")
            
            logger.info(f"Visualizer run started: {commodity} @ {mandi}")
            
            # 1. Query Received
            await send_event(websocket, "query_received", {"commodity": commodity, "mandi": mandi})
            
            start_total = time.time()
            
            # 2. Seasonality Agent
            await send_event(websocket, "seasonality_started")
            s_start = time.time()
            # Running directly in loop for better Windows/Conda stability
            seasonality_output = run_seasonality_agent(commodity, mandi)
            s_duration = (time.time() - s_start) * 1000
            
            await send_event(websocket, "seasonality_completed", 
                           data=seasonality_output.dict(),
                           metadata={"latency_ms": round(s_duration, 2)})
            
            # 3. Arrival Volume Agent
            await send_event(websocket, "arrival_started")
            a_start = time.time()
            arrival_output = run_arrival_volume_agent(commodity, mandi)
            a_duration = (time.time() - a_start) * 1000
            
            await send_event(websocket, "arrival_completed", 
                           data=arrival_output.dict(),
                           metadata={"latency_ms": round(a_duration, 2)})
            
            # 4. External Factors Agent
            await send_event(websocket, "external_started")
            e_start = time.time()
            external_output = run_external_factors_agent(commodity, mandi)
            e_duration = (time.time() - e_start) * 1000
            
            await send_event(websocket, "external_completed", 
                           data=external_output,
                           metadata={"latency_ms": round(e_duration, 2)})
            
            # 5. Ensemble Weights
            await send_event(websocket, "ensemble_weights_computed", 
                           data={
                               "seasonality_weights": seasonality_output.metadata.get("ensemble_log", {}).get("model_weights", {}),
                               "arrival_weights": arrival_output.metadata.get("ensemble_log", {}).get("model_weights", {})
                           })
            
            # 6. Meta-Ensemble Fusion
            await send_event(websocket, "meta_ensemble_started")
            m_start = time.time()
            meta_result = run_meta_ensemble(
                seasonality_output=seasonality_output,
                arrival_output=arrival_output,
                external_impact=external_output["impact_score"],
                external_confidence=external_output["confidence"]
            )
            m_duration = (time.time() - m_start) * 1000
            
            await send_event(websocket, "meta_ensemble_completed", 
                           data=meta_result.to_dict(),
                           metadata={
                               "latency_ms": round(m_duration, 2),
                               "attribution": meta_result.attribution
                           })
            
            # 7. Final Output
            total_duration = (time.time() - start_total) * 1000
            try:
                await send_event(websocket, "final_output", 
                               data=meta_result.to_dict(),
                               metadata={"total_latency_ms": round(total_duration, 2)})
            except Exception as se:
                logger.error(f"Failed to send final output: {se}")
            
            logger.info(f"SUCCESS: Visualizer run complete for {commodity} @ {mandi}")
            print(f"DEBUG: PIPELINE SUCCESS FOR {commodity}")
            
    except WebSocketDisconnect:
        logger.info("Visualizer WebSocket disconnected")
    except Exception as e:
        logger.error(f"CRITICAL VISUALIZER FAILURE: {e}", exc_info=True)
        try:
            await websocket.send_json({"step": "error", "message": str(e)})
        except:
            pass
