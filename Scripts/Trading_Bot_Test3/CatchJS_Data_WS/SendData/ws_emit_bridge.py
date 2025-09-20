# ws_emit_bridge.py  — HUB (server) that broadcasts payloads to all connected clients
import json
import threading
import asyncio
from contextlib import suppress
from typing import Optional, Set, Dict
from itertools import count

import websockets
from websockets import WebSocketServerProtocol, ConnectionClosedOK, ConnectionClosedError
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.SendData.log_uniform import UniformLogger

log = UniformLogger("WS-HUB")

# === Globals ==============================================================
_loop: Optional[asyncio.AbstractEventLoop] = None
_thread: Optional[threading.Thread] = None
_stop_evt = threading.Event()

_clients: Set[WebSocketServerProtocol] = set()
_client_ids: Dict[WebSocketServerProtocol, str] = {}
_id_counter = count(1)

_queue: Optional[asyncio.Queue] = None

_HOST = "127.0.0.1"
_PORT = 8765
SERVE_KW = dict(ping_interval=20, ping_timeout=20, close_timeout=1, max_size=None)

# Logging toggle
_LOGS_ENABLED = True
_waiting_logged = False  # ensure we don't spam "Waiting ..."

def _log(method: str, *args):
    if _LOGS_ENABLED:
        getattr(log, method)(*args)

def _print(text: str):
    if _LOGS_ENABLED:
        print(text)

def _peer(ws: WebSocketServerProtocol) -> str:
    ra = getattr(ws, "remote_address", None)
    if isinstance(ra, (tuple, list)) and len(ra) >= 2:
        return f"{ra[0]}:{ra[1]}"
    return str(ra or "<unknown>")

# === Internals ============================================================
async def _broadcast_worker():
    """Takes dict or list payloads and broadcasts JSON to all clients."""
    assert _queue is not None
    while not _stop_evt.is_set():
        item = await _queue.get()
        if item is None:
            break

        items = item if isinstance(item, list) else [item]
        for elem in items:
            wire = json.dumps(elem)
            _log("sent_wire", wire)  # 📤 [WS-HUB] Sent (json)   : {...}

            dead = []
            for ws in list(_clients):
                try:
                    await ws.send(wire)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                _clients.discard(ws)
                _client_ids.pop(ws, None)

async def _handler(ws: WebSocketServerProtocol):
    """Accept connections; read ACKs so we can log them with client IDs."""
    global _waiting_logged
    cid = f"C{next(_id_counter)}"
    _clients.add(ws)
    _client_ids[ws] = cid

    _log("connected")
    _log("ready")
    _print(f"🔗 [{log.role}] Client id={cid} peer={_peer(ws)}")
    _waiting_logged = False  # we have at least one client now

    logged_disc = False
    try:
        async for msg in ws:  # receivers send ACKs; include id in log line
            _log("got_reply", f"[{cid}] {msg}")
    except (ConnectionClosedOK, ConnectionClosedError) as e:
        _log("disconnected", e.code, f"{e.reason} (id={cid}, peer={_peer(ws)})")
        logged_disc = True
    except Exception as e:
        _log("disconnected", "?", f"{e} (id={cid}, peer={_peer(ws)})")
        logged_disc = True
    finally:
        if not logged_disc:
            code = getattr(ws, "close_code", None)
            reason = getattr(ws, "close_reason", None)
            code_out = code if code is not None else "?"
            reason_out = (reason if reason else "no close frame received or sent") + f" (id={cid}, peer={_peer(ws)})"
            _log("disconnected", code_out, reason_out)

        _clients.discard(ws)
        _client_ids.pop(ws, None)

        # Only print "Waiting ..." when the LAST client leaves (no spam)
        if not _clients and not _waiting_logged:
            _log("waiting")
            _waiting_logged = True

async def _run_server():
    global _queue, _waiting_logged
    _log("starting")
    _queue = asyncio.Queue(maxsize=1000)
    _waiting_logged = False
    async with websockets.serve(_handler, _HOST, _PORT, **SERVE_KW):
        # at startup, server is waiting for the first client
        if not _waiting_logged:
            _log("waiting")
            _waiting_logged = True

        broadcaster = asyncio.create_task(_broadcast_worker())
        try:
            await asyncio.Future()  # run forever
        finally:
            if not broadcaster.done():
                broadcaster.cancel()
                with suppress(asyncio.CancelledError):
                    await broadcaster

# === Public API ==========================================================
def start_server(host: str = "127.0.0.1", port: int = 8765, *, logs: bool = True):
    """Start the hub server (idempotent). Pass logs=False to silence all output."""
    global _HOST, _PORT, _thread, _loop, _LOGS_ENABLED
    if _thread and _thread.is_alive():
        return
    _HOST, _PORT = host, port
    _LOGS_ENABLED = logs
    _stop_evt.clear()

    def _thread_target():
        global _loop
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
        try:
            _loop.run_until_complete(_run_server())
        finally:
            _loop.run_until_complete(_loop.shutdown_asyncgens())
            _loop.close()

    _thread = threading.Thread(target=_thread_target, name="ws-hub", daemon=True)
    _thread.start()

def send(payload):
    """Enqueue payload (dict OR list) for broadcast to all connected clients."""
    if _loop is None or _queue is None:
        return
    def _try_put():
        try:
            _queue.put_nowait(payload)
        except asyncio.QueueFull:
            pass  # drop newest
    _loop.call_soon_threadsafe(_try_put)

def stop():
    """Stop the hub server."""
    global _thread
    if not _thread:
        return
    _log("closing_by_user")
    _stop_evt.set()
    if _loop and _queue:
        with suppress(Exception):
            _loop.call_soon_threadsafe(_queue.put_nowait, None)
    _thread.join(timeout=3)
    _thread = None
    _log("stopped_by_user")
