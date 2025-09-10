# ws_server.py — STRICT UNIFORM LOGS (mirrors client wording exactly)
import asyncio, json
import websockets

SERVE_KW = dict(ping_interval=20, ping_timeout=20, close_timeout=1)
ROLE = "SERVER"
URI = "ws://127.0.0.1:8765"

# ===== uniform logs =====
def _fmt_reason(code, reason):
    r = (reason or "").strip()
    return f"code={code if code is not None else '?'} reason={r if r else '<none>'}"

def log_starting():
    print(f"🚀 [{ROLE}] Starting ...")

def log_waiting():
    print(f"⏳ [{ROLE}] Waiting ...")

def log_connected():
    print(f"✅ [{ROLE}] Connected.")
    print(f"🟢 [{ROLE}] Ready.")

def log_disconnected(code, reason):
    print(f"🔌 [{ROLE}] Disconnected: {_fmt_reason(code, reason)}")

def log_recv_raw(msg):
    print(f"📥 [{ROLE}] Received (raw): {msg}")

def log_recv_summary(side, tf, status):
    print(f"📥 [{ROLE}] Received (summary): {side} {tf}m ({status})")

def log_sent_json(reply):
    print(f"📤 [{ROLE}] Sent back (json): {reply}\n")

# ===== app =====
async def handler(ws):
    # On new client, emit the exact same connect block as client
    log_connected()
    try:
        async for msg in ws:
            try:
                log_recv_raw(msg)
                data = json.loads(msg)
                side = str(data.get("side","")).upper()
                tf = data.get("tf","?")
                status = data.get("status","?")
                log_recv_summary(side, tf, status)

                reply = json.dumps({"message": f"Server received {side} {tf}m ({status})"})
                await ws.send(reply)
                log_sent_json(reply)
            except json.JSONDecodeError:
                print(f"⚠️ [{ROLE}] Bad message: not JSON")
    except websockets.ConnectionClosedOK as e:
        log_disconnected(e.code, e.reason)
        log_waiting()
    except websockets.ConnectionClosedError as e:
        log_disconnected(e.code, e.reason)
        log_waiting()
    except (ConnectionResetError, OSError) as e:
        log_disconnected(None, str(e))
        log_waiting()

async def main():
    log_starting()
    async with websockets.serve(handler, "127.0.0.1", 8765, **SERVE_KW):
        # Server is "waiting" until a client arrives
        log_waiting()
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🟥 [SERVER] Stopped by user.")
