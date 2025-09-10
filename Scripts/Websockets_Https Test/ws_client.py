# ws_client.py (no .closed access; clean reconnects)
import asyncio, json, time, random
import websockets

TF_CHOICES = ["1", "5", "15", "30"]
URI = "ws://127.0.0.1:8765"

CONNECT_KW = dict(ping_interval=20, ping_timeout=20, close_timeout=1)

def make_event():
    tf = random.choice(TF_CHOICES)
    start = int(time.time())
    return {
        "source": "test",
        "side": random.choice(["bull", "bear"]),
        "status": "?",
        "tf": tf,
        "start": start,
        "end": start + int(tf) * 60,
    }

async def talk(ws) -> bool:
    """Return True if user quit intentionally, False if connection dropped."""
    print("✅ Connected.")
    print("↩️  Press ENTER to send a random CVD event. Type 'q' + ENTER to quit.")
    while True:
        user = await asyncio.to_thread(input)
        if user.strip().lower() == "q":
            # Try to close politely; ignore errors if server already died
            try:
                await ws.close(code=1000, reason="client quits")
            except Exception:
                pass
            print("👋 Client closing connection...")
            return True  # user quit

        e = make_event()
        wire = json.dumps(e)
        try:
            await ws.send(wire)
            print(f"📤 Sent (summary): {e['side'].upper()} {e['tf']}m ({e['status']})")
            print(f"📤 Sent (json)   : {wire}")
            reply = await ws.recv()
            print(f"📨 Got reply (raw): {reply}\n")
        except websockets.ConnectionClosedOK as ex:
            print(f"👋 Server closed cleanly: code={getattr(ex, 'code', '?')} reason={getattr(ex, 'reason', '?')}")
            return False  # connection ended, not user quit
        except websockets.ConnectionClosedError as ex:
            print(f"🔌 Server connection error: code={getattr(ex, 'code', '?')} reason={getattr(ex, 'reason', '?')}")
            return False
        except (ConnectionResetError, OSError) as ex:
            print("🔌 Network dropped during send/recv:", ex)
            return False

async def run():
    backoff = 1
    while True:
        try:
            print(f"🔌 Connecting to {URI} ...")
            async with websockets.connect(URI, **CONNECT_KW) as ws:
                user_quit = await talk(ws)
                if user_quit:
                    break  # exit program
                # else: loop to reconnect
        except (ConnectionRefusedError, OSError) as ex:
            print(f"⏳ Cannot connect ({ex}). Retrying in {backoff}s ...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 10)
        except KeyboardInterrupt:
            print("\n🟥 Client stopped by user")
            break

if __name__ == "__main__":
    asyncio.run(run())
