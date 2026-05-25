import asyncio
import websockets
import json

async def test_ws():
    uri = "ws://localhost:8000/ws/visualizer"
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected!")
            await websocket.send(json.dumps({"commodity": "tomato", "mandi": "kolar"}))
            print("Sent query")
            while True:
                response = await websocket.recv()
                msg = json.loads(response)
                print(f"Step: {msg['step']}")
                if msg['step'] == 'final_output':
                    break
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_ws())
