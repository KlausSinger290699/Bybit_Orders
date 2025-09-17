# div_receiver.py
import asyncio, json
import websockets
from log_uniform import UniformLogger

HOST = "127.0.0.1"
PORT = 8765

# WS timings to match the emitters
SERVE_KW = dict(ping_interval=20, ping_timeout=20, close_timeout=1)

log = UniformLogger("RECEIVER")

async def handler(ws):
    log.connected()
    log.ready()
    print()

    try:
        async for msg in ws:
            log.recv_raw(msg)
            try:
                data = json.loads(msg)
            except json.JSONDecodeError as e:
                log.recv_summary("BADJSON", "?", f"{e}")
                continue

            # Accept only our emitter messages (source == "aggr")
            if data.get("source") != "aggr":
                log.recv_summary("IGNORED", str(data.get("tf", "?")), "not-aggr")
                continue

            side = str(data.get("side", "?")).upper()
            status = str(data.get("status", "?"))
            tf = str(data.get("tf", "?"))
            log.recv_summary(side, tf, status)

            # Echo back ACK so browser console can confirm
            ack = {"ack": True, "received": data}
            wire = json.dumps(ack)
            await ws.send(wire)
            log.sent_json(wire)

    except websockets.ConnectionClosedOK as e:
        log.disconnected(e.code, e.reason); log.waiting()
    except websockets.ConnectionClosedError as e:
        log.disconnected(e.code, e.reason); log.waiting()
    except (ConnectionResetError, OSError) as e:
        log.disconnected(None, str(e));     log.waiting()

async def main():
    log.starting()
    async with websockets.serve(handler, HOST, PORT, **SERVE_KW):
        log.waiting()
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.stopped_by_user()



