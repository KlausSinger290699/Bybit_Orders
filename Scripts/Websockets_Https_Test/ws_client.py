# ws_client.py — STRICT UNIFORM LOGS; single "Waiting ..." per cycle; Py 3.11-safe
import asyncio, json, time, random
from contextlib import suppress
import websockets

URI = "ws://127.0.0.1:8765"
TF_CHOICES = ["1", "5", "15", "30"]
CONNECT_KW = dict(ping_interval=20, ping_timeout=20, close_timeout=1)
ROLE = "CLIENT"

# ----- uniform logs -----
def _fmt_reason(code, reason):
    r = (reason or "").strip()
    return f"code={code if code is not None else '?'} reason={r if r else '<none>'}"

def log_starting():    print(f"🚀 [{ROLE}] Starting ...")
def log_waiting():     print(f"⏳ [{ROLE}] Waiting ...")
def log_connected():
    print(f"✅ [{ROLE}] Connected.")
    print(f"🟢 [{ROLE}] Ready.")
def log_prompt():
    print("↩️  Press ENTER to send a random CVD event. Type 'q' + ENTER to quit.")
def log_disconnected(code, reason):  print(f"🔌 [{ROLE}] Disconnected: {_fmt_reason(code, reason)}")
def log_send_summary(side, tf, status): print(f"📤 [{ROLE}] Sent (summary): {side.upper()} {tf}m ({status})")
def log_send_json(wire):               print(f"📤 [{ROLE}] Sent (json)   : {wire}")
def log_got_reply(reply):              print(f"📨 [{ROLE}] Got reply (raw): {reply}\n")

# ----- app -----
def make_event():
    tf = random.choice(TF_CHOICES)
    now = int(time.time())
    return {"source":"test","side":random.choice(["bull","bear"]),"status":"?","tf":tf,"start":now,"end":now+int(tf)*60}

async def _stdin_reader(q: asyncio.Queue):
    while True:
        line = await asyncio.to_thread(input)
        await q.put(line)

async def talk(ws, in_q: asyncio.Queue) -> bool:
    # Always identical connect block
    log_connected()
    log_prompt()

    while True:
        input_task  = asyncio.create_task(in_q.get())
        closed_task = asyncio.create_task(ws.wait_closed())
        done, pending = await asyncio.wait({input_task, closed_task}, return_when=asyncio.FIRST_COMPLETED)

        if closed_task in done:
            if input_task in pending:
                input_task.cancel()
                with suppress(asyncio.CancelledError):
                    await input_task
            # Single, consistent disconnect line; NO "Waiting ..." here
            log_disconnected(ws.close_code, getattr(ws, "close_reason", ""))
            return False

        if closed_task in pending:
            closed_task.cancel()
            with suppress(asyncio.CancelledError):
                await closed_task

        user = input_task.result().strip().lower()
        if user == "q":
            with suppress(Exception):
                await ws.close(code=1000, reason="client quits")
            # Log the same disconnect line for 'q' exits
            log_disconnected(1000, "client quits")
            return True

        e = make_event()
        wire = json.dumps(e)
        try:
            await ws.send(wire)
            log_send_summary(e["side"], e["tf"], e["status"])
            log_send_json(wire)
            reply = await ws.recv()
            log_got_reply(reply)
        except websockets.ConnectionClosedOK as ex:
            log_disconnected(getattr(ex,"code",None), getattr(ex,"reason",""))
            return False
        except websockets.ConnectionClosedError as ex:
            log_disconnected(getattr(ex,"code",None), getattr(ex,"reason",""))
            return False
        except (ConnectionResetError, OSError) as ex:
            log_disconnected(None, str(ex))
            return False

async def run():
    log_starting()
    in_q = asyncio.Queue()
    reader_task = asyncio.create_task(_stdin_reader(in_q))
    backoff = 1
    waiting_shown = False  # ensures exactly ONE "Waiting ..." per reconnect cycle

    try:
        while True:
            if not waiting_shown:
                log_waiting()
                waiting_shown = True

            try:
                async with websockets.connect(URI, **CONNECT_KW) as ws:
                    backoff = 1
                    waiting_shown = False  # reset for the *next* cycle after this session ends
                    user_quit = await talk(ws, in_q)
                    if user_quit:
                        break
            except (ConnectionRefusedError, OSError):
                # Still not available; do NOT print another "Waiting ..."
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 10)
            except KeyboardInterrupt:
                print("\n🟥 [CLIENT] Stopped by user.")
                break
            else:
                # talk() ended due to drop; do NOT print another "Waiting ..." here
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 10)
    finally:
        reader_task.cancel()
        with suppress(asyncio.CancelledError):
            await reader_task

if __name__ == "__main__":
    asyncio.run(run())
