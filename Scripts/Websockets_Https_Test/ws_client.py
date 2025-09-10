# ws_client.py (auto-reconnect while idle; robust stdin; Py 3.11-safe)
import asyncio, json, time, random
from contextlib import suppress
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

async def _stdin_reader(q: asyncio.Queue):
    """Single background stdin reader; pushes lines into a queue."""
    while True:
        # input() blocks in a thread; this task stays alive for the whole program
        line = await asyncio.to_thread(input)
        await q.put(line)

async def talk(ws, in_q: asyncio.Queue) -> bool:
    """Return True if user quit intentionally, False if connection dropped."""
    print("✅ Connected.")
    print("↩️  Press ENTER to send a random CVD event. Type 'q' + ENTER to quit.")

    while True:
        # Race user input vs socket closing
        input_task = asyncio.create_task(in_q.get())
        closed_task = asyncio.create_task(ws.wait_closed())

        done, pending = await asyncio.wait(
            {input_task, closed_task},
            return_when=asyncio.FIRST_COMPLETED,
        )

        if closed_task in done:
            # Server closed while idle → reconnect
            # Cancel the waiting input_task cleanly (reader task keeps running)
            if input_task in pending:
                input_task.cancel()
                with suppress(asyncio.CancelledError):
                    await input_task
            code = getattr(ws, "close_code", None)
            reason = getattr(ws, "close_reason", "")
            print(f"🔌 Server connection ended while idle: code={code} reason={reason}")
            return False

        # We got user input
        # Cancel the closed watcher (it will raise CancelledError on await)
        if closed_task in pending:
            closed_task.cancel()
            with suppress(asyncio.CancelledError):
                await closed_task

        user = input_task.result()
        if user.strip().lower() == "q":
            try:
                await ws.close(code=1000, reason="client quits")
            except Exception:
                pass
            print("👋 Client closing connection...")
            return True

        # Send a random event and wait for reply
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
            return False
        except websockets.ConnectionClosedError as ex:
            print(f"🔌 Server connection error: code={getattr(ex, 'code', '?')} reason={getattr(ex, 'reason', '?')}")
            return False
        except (ConnectionResetError, OSError) as ex:
            print("🔌 Network dropped during send/recv:", ex)
            return False

async def run():
    in_q = asyncio.Queue()
    reader_task = asyncio.create_task(_stdin_reader(in_q))

    backoff = 1
    try:
        while True:
            try:
                print(f"🔌 Connecting to {URI} ...")
                async with websockets.connect(URI, **CONNECT_KW) as ws:
                    user_quit = await talk(ws, in_q)
                    if user_quit:
                        break  # exit program
            except (ConnectionRefusedError, OSError) as ex:
                print(f"⏳ Cannot connect ({ex}). Retrying in {backoff}s ...")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 10)
            except KeyboardInterrupt:
                print("\n🟥 Client stopped by user")
                break
            else:
                backoff = 1  # reset after a successful session
    finally:
        reader_task.cancel()
        with suppress(asyncio.CancelledError):
            await reader_task

if __name__ == "__main__":
    asyncio.run(run())
