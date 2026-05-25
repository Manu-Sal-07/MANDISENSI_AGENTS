import asyncio
import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
from mandisense_ai.utils.event_bus import event_bus
from mandisense_ai.cognition.state_store import MarketMemoryStore

router = APIRouter()
logger = logging.getLogger("CognitionStreaming")

class CognitionStreamManager:
    """
    Manages live synchronization of market cognition.
    Synchronizes the 'Heartbeat' of MandiSense to TraderOS.
    """
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.state_store = MarketMemoryStore()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"TraderOS Terminal connected. Active terminals: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"TraderOS Terminal disconnected. Active terminals: {len(self.active_connections)}")

    async def broadcast_state_update(self, commodity: str, mandi_id: str):
        """
        Broadcasts the evolved market state to all active terminals.
        """
        from datetime import datetime
        state = self.state_store.get_latest_state(commodity, mandi_id)
        if not state:
            return

        state_dict = state.dict() if hasattr(state, 'dict') else (state.model_dump() if hasattr(state, 'model_dump') else state)
        timestamp = datetime.now().isoformat()
        if hasattr(state, 'freshness') and hasattr(state.freshness, 'last_computed'):
            timestamp = state.freshness.last_computed.isoformat()
        elif isinstance(state_dict, dict) and "freshness" in state_dict:
            last_comp = state_dict["freshness"].get("last_computed")
            if isinstance(last_comp, datetime):
                timestamp = last_comp.isoformat()
            elif isinstance(last_comp, str):
                timestamp = last_comp

        payload = {
            "type": "COGNITION_EVOLVED",
            "commodity": commodity,
            "mandi_id": mandi_id,
            "state": state_dict,
            "timestamp": timestamp
        }

        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return super().default(obj)

        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(payload, cls=DateTimeEncoder))
            except Exception as e:
                logger.error(f"Failed to broadcast to terminal: {e}")

    async def broadcast_simulation(self, commodity: str, mandi_id: str, simulated_state: Dict[str, Any]):
        """
        Broadcasts a simulated market state to all active terminals.
        "Revealing future market trajectories."
        """
        from datetime import datetime
        payload = {
            "type": "SIMULATION_EVOLVED",
            "commodity": commodity,
            "mandi_id": mandi_id,
            "state": simulated_state,
            "timestamp": simulated_state["freshness"]["last_computed"] if isinstance(simulated_state, dict) and "freshness" in simulated_state else datetime.now().isoformat()
        }

        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return super().default(obj)

        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(payload, cls=DateTimeEncoder))
            except Exception as e:
                logger.error(f"Failed to broadcast simulation to terminal: {e}")

    async def broadcast_simulation_evolved(self, commodity: str, mandi_id: str, simulated_state: Any, scenario_type: str):
        """
        Broadcasts a simulated market state to all active terminals.
        "Revealing future market trajectories."
        """
        from datetime import datetime
        if hasattr(simulated_state, 'dict'):
            state_dict = simulated_state.dict()
        elif hasattr(simulated_state, 'model_dump'):
            state_dict = simulated_state.model_dump()
        else:
            state_dict = simulated_state

        timestamp = datetime.now().isoformat()
        if hasattr(simulated_state, 'freshness') and hasattr(simulated_state.freshness, 'last_computed'):
            timestamp = simulated_state.freshness.last_computed.isoformat()
        elif isinstance(state_dict, dict) and "freshness" in state_dict:
            last_comp = state_dict["freshness"].get("last_computed")
            if isinstance(last_comp, datetime):
                timestamp = last_comp.isoformat()
            elif isinstance(last_comp, str):
                timestamp = last_comp

        payload = {
            "type": "SIMULATION_EVOLVED",
            "commodity": commodity,
            "mandi_id": mandi_id,
            "scenario_type": scenario_type,
            "state": state_dict,
            "timestamp": timestamp
        }

        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                return super().default(obj)

        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(payload, cls=DateTimeEncoder))
            except Exception as e:
                logger.error(f"Failed to broadcast simulation to terminal: {e}")

stream_manager = CognitionStreamManager()

@router.websocket("/ws/cognition")
async def websocket_cognition(websocket: WebSocket):
    await stream_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Handle potential client-side commands (e.g., subscription changes)
            try:
                msg = json.loads(data)
                if msg.get("type") == "PING":
                    await websocket.send_json({"type": "PONG"})
            except:
                pass
    except WebSocketDisconnect:
        stream_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket streaming error: {e}")
        stream_manager.disconnect(websocket)
