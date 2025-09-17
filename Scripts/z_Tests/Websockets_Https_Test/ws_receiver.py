# receiver.py
import asyncio, json
import websockets
from log_uniform import UniformLogger

SERVE_KW = dict(ping_interval=20, ping_timeout=20, close_timeout=1)

log = UniformLogger("RECEIVER")

async def handler(ws):
    log.connected()
    log.ready()
    print()

    try:
        async for msg in ws:
            log.recv_raw(msg)
            data = json.loads(msg)
            side = str(data.get("side", "")).upper()
            tf = data.get("tf", "?")
            status = data.get("status", "?")
            log.recv_summary(side, tf, status)

            reply = json.dumps({"message": f"Receiver got {side} {tf}m ({status})"})
            await ws.send(reply)
            log.sent_json(reply)
    except websockets.ConnectionClosedOK as e:
        log.disconnected(e.code, e.reason)
        log.waiting()
    except websockets.ConnectionClosedError as e:
        log.disconnected(e.code, e.reason)
        log.waiting()
    except (ConnectionResetError, OSError) as e:
        log.disconnected(None, str(e))
        log.waiting()

async def main():
    log.starting()
    async with websockets.serve(handler, "127.0.0.1", 8765, **SERVE_KW):
        log.waiting()
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.stopped_by_user()
