import asyncio
import sys

import websockets


async def main() -> None:
    port = sys.argv[1] if len(sys.argv) > 1 else "8000"
    uri = f"ws://127.0.0.1:{port}/v1/ws/cognition"
    async with websockets.connect(uri) as websocket:
        print("COGNITION_WS_CONNECTED")
        await websocket.send('{"type":"PING"}')
        print(await asyncio.wait_for(websocket.recv(), timeout=5))


if __name__ == "__main__":
    asyncio.run(main())
