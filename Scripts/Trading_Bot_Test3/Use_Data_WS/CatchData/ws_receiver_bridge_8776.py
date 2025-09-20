# ws_receiver_bridge_8765.py — receiver CLIENT that waits & retries; prints summaries; ACKs each msg
import asyncio
import json
import websockets
from websockets import ConnectionClosedOK, ConnectionClosedError

from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.SendData.log_uniform import UniformLogger

log = UniformLogger("WS-RECV", show_wire=False, show_raw=False)

def _maybe_pivots(d: dict) -> dict:
    """Accept both flat keys and nested under 'pivots'."""
    piv = d.get("pivots")
    return piv if isinstance(piv, dict) else d

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

async def _recv_loop(ws):
    async for msg in ws:
        try:
            payload = json.loads(msg)
        except json.JSONDecodeError:
            print(f"📥 [WS-RECV] Raw: {msg}")
            continue

        if isinstance(payload, dict):
            side = payload.get("side", "-")
            tf = payload.get("tf_sec", "-")
            status = payload.get("status", "-")
            log.recv_summary(side, str(tf), status)
            print(f"    → {summarize_bridge_payload(payload)}")
            ack = json.dumps({
                "ok": True, "message": "receiver ack",
                "tradable": bool(payload.get("Tradable", False)),
                "sl": payload.get("SL")
            })
            await ws.send(ack)
            continue

        if isinstance(payload, list):
            for obj in payload:
                if not isinstance(obj, dict):
                    continue
                side = obj.get("side", "-")
                tf = obj.get("tf_sec", "-")
                status = obj.get("status", "-")
                log.recv_summary(side, str(tf), status)
                print(f"    → {summarize_bridge_payload(obj)}")
                ack = json.dumps({
                    "ok": True, "message": "receiver ack",
                    "tradable": bool(obj.get("Tradable", False)),
                    "sl": obj.get("SL")
                })
                await ws.send(ack)
            continue

        print(f"📥 [WS-RECV] Unsupported shape: {type(payload)}")

async def run(uri: str = "ws://127.0.0.1:8765"):
    log.starting()
    backoff = 1
    waiting_logged = False            # print "Waiting ..." once per offline stretch
    had_connected = False             # true after first successful connect
    disc_logged_this_offline = False  # single "Disconnected ..." per offline stretch

    while True:
        try:
            if not waiting_logged:
                log.waiting()
                waiting_logged = True

            async with websockets.connect(
                uri, ping_interval=20, ping_timeout=20, close_timeout=1, max_size=None
            ) as ws:
                # online
                backoff = 1
                waiting_logged = False
                disc_logged_this_offline = False
                had_connected = True
                log.connected()
                log.ready()
                print()
                await _recv_loop(ws)

        except ConnectionClosedOK as e:
            if had_connected and not disc_logged_this_offline:
                log.disconnected(e.code, e.reason)
                disc_logged_this_offline = True
        except ConnectionClosedError as e:
            if had_connected and not disc_logged_this_offline:
                log.disconnected(e.code, e.reason)
                disc_logged_this_offline = True
        except OSError as e:
            if had_connected and not disc_logged_this_offline:
                log.disconnected("?", str(e))
                disc_logged_this_offline = True
        except Exception as e:
            if had_connected and not disc_logged_this_offline:
                log.disconnected("?", str(e))
                disc_logged_this_offline = True

        # offline; print "Waiting ..." once per stretch
        if not waiting_logged:
            log.waiting()
            waiting_logged = True

        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 10)

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        log.closing_by_user()
        log.stopped_by_user()
