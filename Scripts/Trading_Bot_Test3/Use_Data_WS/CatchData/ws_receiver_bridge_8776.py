# ws_receiver_bridge_8765.py — receiver CLIENT that waits & retries; prints summaries; ACKs each msg
import asyncio
import json
import threading
from contextlib import suppress
from typing import Optional

import websockets
from websockets import ConnectionClosedOK, ConnectionClosedError

from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.SendData.log_uniform import UniformLogger

# Logger (actual printing is gated by the toggles below)
log = UniformLogger("WS-RECV", show_wire=False, show_raw=False)

# === Globals ==============================================================
_loop: Optional[asyncio.AbstractEventLoop] = None
_thread: Optional[threading.Thread] = None
_stop_evt = threading.Event()

_URI = "ws://127.0.0.1:8765"

# Logging toggles (default silent, like hub now)
_LOGS_ENABLED = False   # general logs: starting, waiting, connected, ready, summaries, disconnect
_LOG_WIRE = False       # ONLY the "sent back (json)" ACK lines

def _log(method: str, *args):
    if _LOGS_ENABLED:
        getattr(log, method)(*args)

def _log_sent_json(payload: str):
    if _LOG_WIRE:
        log.sent_json(payload)

# === Helpers ==============================================================

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
        # Parse payload
        try:
            payload = json.loads(msg)
        except json.JSONDecodeError:
            if _LOGS_ENABLED:
                print(f"📥 [WS-RECV] Raw: {msg}")
            continue

        # Single object
        if isinstance(payload, dict):
            side = payload.get("side", "-")
            tf = payload.get("tf_sec", "-")
            status = payload.get("status", "-")
            _log("recv_summary", side, str(tf), status)
            if _LOGS_ENABLED:
                print(f"    → {summarize_bridge_payload(payload)}")
            ack = json.dumps({
                "ok": True, "message": "receiver ack",
                "tradable": bool(payload.get("Tradable", False)),
                "sl": payload.get("SL")
            })
            await ws.send(ack)
            _log_sent_json(ack)
            continue

        # Array of objects
        if isinstance(payload, list):
            for obj in payload:
                if not isinstance(obj, dict):
                    continue
                side = obj.get("side", "-")
                tf = obj.get("tf_sec", "-")
                status = obj.get("status", "-")
                _log("recv_summary", side, str(tf), status)
                if _LOGS_ENABLED:
                    print(f"    → {summarize_bridge_payload(obj)}")
                ack = json.dumps({
                    "ok": True, "message": "receiver ack",
                    "tradable": bool(obj.get("Tradable", False)),
                    "sl": obj.get("SL")
                })
                await ws.send(ack)
                _log_sent_json(ack)
            continue

        if _LOGS_ENABLED:
            print(f"📥 [WS-RECV] Unsupported shape: {type(payload)}")

# === Main connect loop =====================================================

async def run(uri: str = "ws://127.0.0.1:8765", *, noisylogs: bool = False, logs: bool = False):
    """
    Standalone entry (awaitable). Use from __main__ or call via asyncio.
    noisylogs=True  -> print EVERYTHING (incl. 'Sent back (json)')
    logs=True       -> print all EXCEPT 'Sent back (json)'
    both False      -> silent
    both True       -> everything
    """
    global _LOGS_ENABLED, _LOG_WIRE

    # Set toggles per call
    if noisylogs:
        _LOGS_ENABLED = True
        _LOG_WIRE = True
    elif logs:
        _LOGS_ENABLED = True
        _LOG_WIRE = False
    else:
        _LOGS_ENABLED = False
        _LOG_WIRE = False

    _log("starting")
    backoff = 1
    waiting_logged = False            # print "Waiting ..." once per offline stretch
    had_connected = False             # true after first successful connect
    disc_logged_this_offline = False  # single "Disconnected ..." per offline stretch

    while not _stop_evt.is_set():
        try:
            if not waiting_logged:
                _log("waiting")
                waiting_logged = True

            async with websockets.connect(
                uri, ping_interval=20, ping_timeout=20, close_timeout=1, max_size=None
            ) as ws:
                # online
                backoff = 1
                waiting_logged = False
                disc_logged_this_offline = False
                had_connected = True
                _log("connected")
                _log("ready")
                if _LOGS_ENABLED:
                    print()
                await _recv_loop(ws)

        except ConnectionClosedOK as e:
            if had_connected and not disc_logged_this_offline:
                _log("disconnected", e.code, e.reason)
                disc_logged_this_offline = True
        except ConnectionClosedError as e:
            if had_connected and not disc_logged_this_offline:
                _log("disconnected", e.code, e.reason)
                disc_logged_this_offline = True
        except OSError as e:
            if had_connected and not disc_logged_this_offline:
                _log("disconnected", "?", str(e))
                disc_logged_this_offline = True
        except Exception as e:
            if had_connected and not disc_logged_this_offline:
                _log("disconnected", "?", str(e))
                disc_logged_this_offline = True

        # offline; print "Waiting ..." once per stretch
        if _stop_evt.is_set():
            break
        if not waiting_logged:
            _log("waiting")
            waiting_logged = True

        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 10)

# === Threaded API for main.py =============================================

def _thread_target():
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    try:
        _loop.run_until_complete(run(_URI, noisylogs=_LOG_WIRE and _LOGS_ENABLED,
                                     logs=(not _LOG_WIRE) and _LOGS_ENABLED))
    finally:
        _loop.run_until_complete(_loop.shutdown_asyncgens())
        _loop.close()

def start_client(uri: str = "ws://127.0.0.1:8765", *, noisylogs: bool = False, logs: bool = False):
    """
    Start receiver in a background thread (idempotent).
    noisylogs=True  -> print EVERYTHING (incl. 'Sent back (json)')
    logs=True       -> print all EXCEPT 'Sent back (json)'
    """
    global _thread, _URI, _LOGS_ENABLED, _LOG_WIRE
    if _thread and _thread.is_alive():
        return
    _URI = uri

    # same precedence as hub
    if noisylogs:
        _LOGS_ENABLED = True
        _LOG_WIRE = True
    elif logs:
        _LOGS_ENABLED = True
        _LOG_WIRE = False
    else:
        _LOGS_ENABLED = False
        _LOG_WIRE = False

    _stop_evt.clear()
    _thread = threading.Thread(target=_thread_target, name="ws-recv", daemon=True)
    _thread.start()

def stop_client():
    """Stop the background receiver gracefully (idempotent)."""
    global _thread
    if not _thread:
        return
    _stop_evt.set()
    # wake sleeps sooner
    if _loop and _loop.is_running():
        try:
            _loop.call_soon_threadsafe(lambda: None)
        except Exception:
            pass
    _thread.join(timeout=3)
    _thread = None

# === CLI / standalone ======================================================
if __name__ == "__main__":
    try:
        # Standalone defaults: silent (like hub’s default)
        asyncio.run(run(_URI, noisylogs=True, logs=True))
    except KeyboardInterrupt:
        _log("closing_by_user")
        _log("stopped_by_user")
