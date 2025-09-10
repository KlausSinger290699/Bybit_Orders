import asyncio, json, time
import websockets

EVENTS = [
    {"source": "test", "side": "bear", "status": "?", "tf": "15", "start": int(time.time()), "end": int(time.time()) + 900},
    {"source": "test", "side": "bull", "status": "?", "tf": "5",  "start": int(time.time()), "end": int(time.time()) + 300},
]

async def run():
    uri = "ws://127.0.0.1:8765"
    print(f"🔌 Connecting to {uri} ...")
    async with websockets.connect(uri) as ws:
        print("✅ Connected. Sending events...")
        for e in EVENTS:
            await ws.send(json.dumps(e))
            print(f"📤 Sent: {e}")
            reply = await ws.recv()
            print(f"📨 Got reply: {reply}")

if __name__ == "__main__":
    asyncio.run(run())
