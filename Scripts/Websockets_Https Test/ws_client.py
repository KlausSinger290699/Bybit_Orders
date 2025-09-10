# ws_client.py
import asyncio, json, time, random
import websockets

TF_CHOICES = ["1", "5", "15", "30"]

def make_event():
    tf = random.choice(TF_CHOICES)
    start = int(time.time())
    return {
        "source": "test",
        "side": random.choice(["bull", "bear"]),
        "status": "?",
        "tf": tf,
        "start": start,
        "end": start + int(tf)*60,
    }

async def run():
    uri = "ws://127.0.0.1:8765"
    print(f"🔌 Connecting to {uri} ...")
    # (optional) tune pings on client side too
    async with websockets.connect(uri, ping_interval=20, ping_timeout=20) as ws:
        print("✅ Connected.")
        print("↩️  Press ENTER to send a random CVD event. Type 'q' and ENTER to quit.")
        while True:
            user = await asyncio.to_thread(input)   # <-- non-blocking
            if user.strip().lower() == "q":
                break

            e = make_event()
            await ws.send(json.dumps(e))
            print(f"📤 Sent: {e['side'].upper()} {e['tf']}m ({e['status']})")
            reply = await ws.recv()
            print(f"📨 Got reply: {reply}")

if __name__ == "__main__":
    asyncio.run(run())
