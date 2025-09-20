# ws_emit_bridge.py  — HUB (server) that broadcasts payloads to all connected clients
import json
import threading
import asyncio
from contextlib import suppress
from typing import Optional, Set

import websockets
from websockets import WebSocketServerProtocol
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.SendData.log_uniform import UniformLogger

log = UniformLogger("WS-HUB")

# === Globals ==============================================================
_loop: Optional[asyncio.AbstractEventLoop] = None
_thread: Optional[threading.Thread] = None
_stop_evt = threading.Event()

_clients: Set[WebSocketServerProtocol] = set()
_queue: Optional[asyncio.Queue] = None

_HOST = "127.0.0.1"
_PORT = 8765
SERVE_KW = dict(ping_interval=20, ping_timeout=20, close_timeout=1, max_size=None)

# Logging toggle
_LOGS_ENABLED = True


def _log(method: str, *args):
    """Call a logger method only if logs are enabled."""
    if _LOGS_ENABLED:
        getattr(log, method)(*args)


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
            _log("sent_wire", wire)  # ugly full JSON, like before

            dead = []
            for ws in list(_clients):
                try:
                    await ws.send(wire)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                _clients.discard(ws)


async def _handler(ws: WebSocketServerProtocol):
    """Accept connections. Ignore inbound messages (pure broadcast hub)."""
    _clients.add(ws)
    _log("connected")
    _log("ready")
    try:
        async for _ in ws:
            # Ignore any inbound chatter from clients
            pass
    except Exception as e:
        _log("disconnected", "?", str(e))
    finally:
        _clients.discard(ws)
        _log("waiting")


async def _run_server():
    global _queue
    _log("starting")
    _queue = asyncio.Queue(maxsize=1000)
    async with websockets.serve(_handler, _HOST, _PORT, **SERVE_KW):
        _log("waiting")
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
    """Start the hub server (idempotent).
    Pass logs=False to silence all console output from this module.
    """
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
            # drop newest
            pass

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
