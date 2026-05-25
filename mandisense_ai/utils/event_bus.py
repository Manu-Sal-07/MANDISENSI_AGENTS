import asyncio
import json
import time
import logging
from typing import List, Dict, Any
from fastapi import WebSocket

logger = logging.getLogger("event_bus")

class EventBus:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket connection. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def emit(self, step: str, status: str = "running", data: Any = None, metadata: Any = None):
        """
        Broadcasts an event to all connected WebSocket clients.
        """
        event = {
            "step": step,
            "status": status,
            "timestamp": time.time(),
            "data": data,
            "metadata": metadata
        }
        
        # Logging for debugging
        print(f"[TRACE EVENT] {event}")
        
        if not self.active_connections:
            return

        message = json.dumps(event, default=str)
        
        # Send to all connected clients
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error sending event to WebSocket: {e}")
                disconnected.append(connection)
        
        # Clean up dead connections
        for dead in disconnected:
            self.disconnect(dead)

    def sync_emit(self, step: str, status: str = "running", data: Any = None, metadata: Any = None):
        """
        Synchronous wrapper for emit.
        """
        try:
            # Try to get the running loop (usually the main one in FastAPI)
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # If no loop is running in this thread, try to get the default loop
                loop = asyncio.get_event_loop()

            if loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.emit(step, status, data, metadata), 
                    loop
                )
            else:
                loop.run_until_complete(self.emit(step, status, data, metadata))
        except Exception as e:
            # Fallback: create a temporary loop for this thread if absolutely necessary,
            # though this won't reach the main thread's WebSocket connections.
            # In a FastAPI context, we really want run_coroutine_threadsafe on the main loop.
            try:
                # Last resort for background threads
                new_loop = asyncio.new_event_loop()
                new_loop.run_until_complete(self.emit(step, status, data, metadata))
                new_loop.close()
            except Exception:
                print(f"[EVENT BUS ERROR] Could not emit event {step}: {e}")

# Global singleton
event_bus = EventBus()
