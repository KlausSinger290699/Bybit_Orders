# ws_receiver_bridge.py
import asyncio
import json
import traceback
import websockets
from log_uniform import UniformLogger

SERVE_KW = dict(ping_interval=20, ping_timeout=20, close_timeout=1, max_size=None)
log = UniformLogger("WS-RECV")

def summarize_bridge_payload(d: dict) -> str:
    tradable = d.get("Tradable")
    L1 = d.get("L1"); T1 = d.get("T1")
    L2 = d.get("L2"); T2 = d.get("T2")
    L3 = d.get("L3"); T3 = d.get("T3")
    L4 = d.get("L4"); T4 = d.get("T4")
    SL = d.get("SL")
    return (f"L1={L1} T1={T1} | L2={L2} T2={T2} | "
            f"L3={L3} T3={T3} | L4={L4} T4={T4} | SL={SL} | Tradable={tradable}")

async def handler(ws):
    log.connected(); log.ready(); print()
    try:
        async for msg in ws:
            log.recv_raw(msg)
            try:
                d = json.loads(msg)
            except json.JSONDecodeError:
                err = json.dumps({"ok": False, "error": "invalid_json"})
                await ws.send(err); log.sent_json(err); continue

            if not isinstance(d, dict):
                # Hard reject non-dicts to avoid internal errors
                err = json.dumps({"ok": False, "error": "expected_object"})
                await ws.send(err); log.sent_json(err); continue

            summary = summarize_bridge_payload(d)
            log.recv_summary("-", "-", "-")
            print(f"    → {summary}")

            reply = json.dumps({
                "ok": True,
                "message": "bridge received divergence packet",
                "tradable": bool(d.get("Tradable", False)),
                "sl": d.get("SL", None),
            })
            await ws.send(reply); log.sent_json(reply)

    except websockets.ConnectionClosedOK as e:
        log.disconnected(e.code, e.reason); log.waiting()
    except websockets.ConnectionClosedError as e:
        log.disconnected(e.code, e.reason); log.waiting()
    except Exception as e:
        # Print full traceback to see the real cause if anything slips through
        traceback.print_exc()
        log.disconnected(None, f"unhandled: {e}"); log.waiting()

async def main():
    log.starting()
    async with websockets.serve(handler, "127.0.0.1", 8765, **SERVE_KW):
        log.waiting()
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.closing_by_user()
        log.stopped_by_user()
