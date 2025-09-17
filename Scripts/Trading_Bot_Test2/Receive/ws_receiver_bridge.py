# ws_receiver_bridge.py
import asyncio
import json
import websockets
from log_uniform import UniformLogger

# Same server kwargs as your sample receiver
SERVE_KW = dict(ping_interval=20, ping_timeout=20, close_timeout=1)

log = UniformLogger("WS-RECV")

def summarize_bridge_payload(data: dict) -> str:
    """Compact one-line summary tailored to bull_div_reader payloads."""
    tradable = data.get("Tradable")
    L1 = data.get("L1"); T1 = data.get("T1")
    L2 = data.get("L2"); T2 = data.get("T2")
    L3 = data.get("L3"); T3 = data.get("T3")
    L4 = data.get("L4"); T4 = data.get("T4")
    SL = data.get("SL")

    return (
        f"L1={L1} T1={T1} | "
        f"L2={L2} T2={T2} | "
        f"L3={L3} T3={T3} | "
        f"L4={L4} T4={T4} | "
        f"SL={SL} | Tradable={tradable}"
    )

async def handler(ws):
    log.connected()
    log.ready()
    print()

    try:
        async for msg in ws:
            # Raw log (exactly like your template)
            log.recv_raw(msg)

            # Parse JSON (robust-ish)
            try:
                data = json.loads(msg)
            except json.JSONDecodeError:
                # Send back a structured error so the emitter can see it
                err = json.dumps({"ok": False, "error": "invalid_json"})
                await ws.send(err)
                log.sent_json(err)
                continue

            # Bridge payload summary
            summary = summarize_bridge_payload(data)
            # Reuse the summary log slot (keeps same style)
            # We'll display "TF" as "-" and "status" as "-" since this payload
            # is L1..L4/T1..T4/Tradable/SL (no side/tf/status).
            log.recv_summary("-", "-", "-")
            print(f"    → {summary}")

            # Echo back an acknowledgment (mirroring your receiver.py)
            reply = json.dumps({
                "ok": True,
                "message": "bridge received divergence packet",
                "tradable": bool(data.get("Tradable", False)),
                "sl": data.get("SL", None)
            })
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
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.stopped_by_user()
