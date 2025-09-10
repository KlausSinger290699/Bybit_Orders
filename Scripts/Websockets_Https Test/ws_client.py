import asyncio, json, time, random
import websockets

TF_CHOICES = ["1", "5", "15", "30"]  # minutes

def make_event():
    side = random.choice(["bull", "bear"])
    tf = random.choice(TF_CHOICES)
    status = "?"  # keep as your pending marker
    start = int(time.time())
    end = start + int(tf) * 60
    return {
        "source": "test",
        "side": side,
        "status": status,
        "tf": tf,
        "start": start,
        "end": end,
    }

async def run():
    uri = "ws://127.0.0.1:8765"
    print(f"🔌 Connecting to {uri} ...")
    async with websockets.connect(uri) as ws:
        print("✅ Connected.")
        print("↩️  Press ENTER to send a random CVD event (bull/bear). Type 'q' + ENTER to quit.")
        while True:
            try:
                user = input()
            except (EOFError, KeyboardInterrupt):
                break
            if user.strip().lower() == "q":
                break

            e = make_event()
            await ws.send(json.dumps(e))
            print(f"📤 Sent: {e['side'].upper()} {e['tf']}m ({e['status']})")
            reply = await ws.recv()
            print(f"📨 Got reply: {reply}")

if __name__ == "__main__":
    asyncio.run(run())