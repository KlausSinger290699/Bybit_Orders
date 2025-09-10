import asyncio, json
import websockets

async def handler(ws):
    print("✅ Server: client connected")
    async for msg in ws:
        try:
            data = json.loads(msg)
            side = data.get("side")
            tf = data.get("tf")
            status = data.get("status")
            print(f"📥 Received: {side.upper()} {tf}m ({status})")

            # Send back a clear message (no "ack")
            reply = {"message": f"Server received {side.upper()} {tf}m ({status})"}
            await ws.send(json.dumps(reply))
        except Exception as e:
            print("⚠️ Bad message:", e)

async def main():
    async with websockets.serve(handler, "127.0.0.1", 8765):
        print("🔊 WS server listening on ws://127.0.0.1:8765")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
