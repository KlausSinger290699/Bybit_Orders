# emit_smoke_test.py
import asyncio, json, time, websockets

URI = "ws://127.0.0.1:8765"

async def main():
    async with websockets.connect(URI) as ws:
        evt = {
            "source":"aggr",
            "side":"bull",
            "status":"?",
            "tf":"15",
            "start": int(time.time())-900,
            "end":   int(time.time()),
            "t": int(time.time()*1000)
        }
        await ws.send(json.dumps(evt))
        print("sent:", evt)
        ack = await ws.recv()
        print("ack :", ack)

if __name__ == "__main__":
    asyncio.run(main())
