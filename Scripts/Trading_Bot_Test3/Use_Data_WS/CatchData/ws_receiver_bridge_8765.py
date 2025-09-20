# ws_receiver_client.py — connect to the hub and print summaries (dict or list)
import asyncio
import json
import websockets
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.SendData.log_uniform import UniformLogger

log = UniformLogger("WS-RECV", show_wire=False, show_raw=False)

def _maybe_pivots(d: dict) -> dict:
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

async def run(uri="ws://127.0.0.1:8765"):
    log.starting()
    async with websockets.connect(uri, ping_interval=20, ping_timeout=20, close_timeout=1, max_size=None) as ws:
        log.connected(); log.ready(); print()
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
            elif isinstance(payload, list):
                for obj in payload:
                    if isinstance(obj, dict):
                        side = obj.get("side", "-")
                        tf = obj.get("tf_sec", "-")
                        status = obj.get("status", "-")
                        log.recv_summary(side, str(tf), status)
                        print(f"    → {summarize_bridge_payload(obj)}")
            else:
                print(f"📥 [WS-RECV] Unsupported shape: {type(payload)}")

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        log.closing_by_user()
        log.stopped_by_user()
