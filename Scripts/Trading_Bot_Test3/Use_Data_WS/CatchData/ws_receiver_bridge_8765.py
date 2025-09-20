# ws_receiver_bridge.py
import asyncio
import json
import traceback
import websockets

from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.SendData.log_uniform import UniformLogger

SERVE_KW = dict(ping_interval=20, ping_timeout=20, close_timeout=1, max_size=None)
log = UniformLogger("WS-RECV", show_wire=False, show_raw=False)  # flip True for verbose


def _maybe_pivots(d: dict) -> dict:
    """
    Accept both flat keys and nested under 'pivots'.
    Returns a dict that has L1..L4/H1..H4 if present (or {}).
    """
    piv = d.get("pivots")
    if isinstance(piv, dict):
        return piv
    return d  # assume flat


def summarize_bridge_payload(d: dict) -> str:
    piv = _maybe_pivots(d)
    L1 = piv.get("L1"); T1 = d.get("T1")
    L2 = piv.get("L2"); T2 = d.get("T2")
    L3 = piv.get("L3"); T3 = d.get("T3")
    L4 = piv.get("L4"); T4 = d.get("T4")
    SL = d.get("SL")
    tradable = d.get("Tradable")
    return (f"L1={L1} T1={T1} | L2={L2} T2={T2} | "
            f"L3={L3} T3={T3} | L4={L4} T4={T4} | SL={SL} | Tradable={tradable}")


async def _handle_one(obj: dict, ws):
    # Pull common summary fields if available
    side = obj.get("side", "-")
    tf = obj.get("tf_sec", "-")
    status = obj.get("status", "-")

    # Log summarized line with actual values
    log.recv_summary(side, str(tf), status)
    print(f"    → {summarize_bridge_payload(obj)}")

    # Minimal structured reply
    reply = json.dumps({
        "ok": True,
        "message": "bridge received divergence packet",
        "tradable": bool(obj.get("Tradable", False)),
        "sl": obj.get("SL", None),
    })
    await ws.send(reply)
    log.sent_json(reply)


async def handler(ws):
    log.connected(); log.ready(); print()
    try:
        async for msg in ws:
            log.recv_raw(msg)
            try:
                payload = json.loads(msg)
            except json.JSONDecodeError:
                err = json.dumps({"ok": False, "error": "invalid_json"})
                await ws.send(err); log.sent_json(err); continue

            # Accept object OR array-of-objects
            if isinstance(payload, dict):
                await _handle_one(payload, ws)
                continue
            if isinstance(payload, list):
                for obj in payload:
                    if isinstance(obj, dict):
                        await _handle_one(obj, ws)
                continue

            # Hard reject other shapes
            err = json.dumps({"ok": False, "error": "expected_object_or_array"})
            await ws.send(err); log.sent_json(err)

    except websockets.ConnectionClosedOK as e:
        log.disconnected(e.code, e.reason); log.waiting()
    except websockets.ConnectionClosedError as e:
        log.disconnected(e.code, e.reason); log.waiting()
    except Exception as e:
        traceback.print_exc()
        log.disconnected(None, f"unhandled: {e}"); log.waiting()


async def main():
    log.starting()
    async with websockets.serve(handler, "127.0.0.1", 8765, **SERVE_KW):
        log.waiting()
        await asyncio.Future()  # run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.closing_by_user()
        log.stopped_by_user()
