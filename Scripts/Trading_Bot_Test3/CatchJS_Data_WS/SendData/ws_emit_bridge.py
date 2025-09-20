# ws_emit_bridge.py
import json
import threading
import asyncio
from contextlib import suppress
from typing import Optional

import websockets
from websockets import ConnectionClosedOK, ConnectionClosedError

from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.SendData.log_uniform import UniformLogger

log = UniformLogger("WS-EMIT")  # leave default: it prints JSON payloads

CONNECT_KW = dict(ping_interval=20, ping_timeout=20, close_timeout=1)

_URI: Optional[str] = None
_loop: Optional[asyncio.AbstractEventLoop] = None
_thread: Optional[threading.Thread] = None
_queue: Optional[asyncio.Queue] = None
_stop_evt = threading.Event()

_is_connected = False
_wait_logged = False


async def _sender(ws, queue: asyncio.Queue):
    """Send loop. On any send error, exit to trigger reconnect."""
    while not _stop_evt.is_set():
        item = await queue.get()
        if item is None:
            break

        items = item if isinstance(item, list) else [item]
        for elem in items:
            try:
                wire = json.dumps(elem)
                await ws.send(wire)
                log.sent_wire(wire)   # 👈 back to JSON dump style
            except (ConnectionClosedOK, ConnectionClosedError, OSError, ConnectionResetError) as e:
                code = getattr(e, 'code', '?')
                reason = getattr(e, 'reason', str(e))
                log.disconnected(code, reason)
                return
            except Exception as e:
                log.disconnected("?", f"send failed: {e}")
                return


async def _receiver(ws):
    """Recv loop. On any disconnect, just return (no raise)."""
    try:
        async for msg in ws:
            log.got_reply(msg)
    except (ConnectionClosedOK, ConnectionClosedError, OSError, ConnectionResetError) as e:
        code = getattr(e, 'code', '?')
        reason = getattr(e, 'reason', str(e))
        log.disconnected(code, reason)
        return
    except Exception as e:
        log.disconnected("?", f"recv failed: {e}")
        return


async def _session(uri: str):
    global _is_connected, _queue, _wait_logged

    async with websockets.connect(uri, **CONNECT_KW) as ws:
        _is_connected = True
        _wait_logged = False
        log.connected()
        log.ready()

        q = asyncio.Queue()
        _queue = q

        send_task = asyncio.create_task(_sender(ws, q))
        recv_task = asyncio.create_task(_receiver(ws))
        try:
            await asyncio.wait({send_task, recv_task}, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for t in (send_task, recv_task):
                if t and not t.done():
                    t.cancel()
                    with suppress(asyncio.CancelledError):
                        await t

            _queue = None
            try:
                while not q.empty():
                    q.get_nowait()
            except Exception:
                pass
            _is_connected = False


async def _run(uri: str):
    global _wait_logged
    log.starting()
    backoff = 1

    while not _stop_evt.is_set():
        if not _wait_logged:
            log.waiting()
            _wait_logged = True

        try:
            await _session(uri)
        except Exception:
            pass

        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 10)

    if _queue is not None:
        try:
            await _queue.put(None)
        except Exception:
            pass


def start(uri: str):
    global _URI, _loop, _thread
    if _thread and _thread.is_alive():
        return
    _URI = uri
    _stop_evt.clear()

    def _thread_target():
        global _loop
        _loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_loop)
        try:
            _loop.run_until_complete(_run(_URI))
        finally:
            _loop.run_until_complete(_loop.shutdown_asyncgens())
            _loop.close()

    _thread = threading.Thread(target=_thread_target, name="ws-emit-bridge", daemon=True)
    _thread.start()


def send(payload):
    """Enqueue payload (dict OR list). Dropped if not connected."""
    if not _is_connected or _loop is None or _queue is None:
        return
    _loop.call_soon_threadsafe(_queue.put_nowait, payload)


def stop():
    global _thread
    if not _thread:
        return
    log.closing_by_user()
    _stop_evt.set()
    if _loop and _queue:
        with suppress(Exception):
            _loop.call_soon_threadsafe(_queue.put_nowait, None)
    _thread.join(timeout=3)
    _thread = None
    log.stopped_by_user()
