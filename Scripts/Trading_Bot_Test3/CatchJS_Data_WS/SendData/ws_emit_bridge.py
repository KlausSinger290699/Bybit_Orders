import json
import threading
import asyncio
from contextlib import suppress
from typing import Optional

import websockets
from websockets import ConnectionClosedOK, ConnectionClosedError

# --- verbosity toggle (default QUIET for clean console) ---
_VERBOSE = False
def set_verbose(flag: bool):
    global _VERBOSE
    _VERBOSE = bool(flag)

def _p(msg: str):
    if _VERBOSE:
        print(msg)

CONNECT_KW = dict(ping_interval=20, ping_timeout=20, close_timeout=1)

_URI: Optional[str] = None
_loop: Optional[asyncio.AbstractEventLoop] = None
_thread: Optional[threading.Thread] = None
_queue: Optional[asyncio.Queue] = None
_stop_evt = threading.Event()


async def _sender(ws, queue: asyncio.Queue):
    while not _stop_evt.is_set():
        item = await queue.get()
        if item is None or item is _stop_evt:
            break
        wire = json.dumps(item)
        await ws.send(wire)
        _p(f"📤 [WS-EMIT] Sent (json)   : {wire}")


async def _receiver(ws):
    try:
        async for msg in ws:
            _p(f"📨 [WS-EMIT] Got reply (raw): {msg}\n")
    except ConnectionClosedOK as e:
        _p(f"🔌 [WS-EMIT] Disconnected: code={e.code} reason={getattr(e, 'reason', '')}")
        raise
    except ConnectionClosedError as e:
        _p(f"🔌 [WS-EMIT] Disconnected: code={e.code} reason={getattr(e, 'reason', '')}")
        raise


async def _session(uri: str, queue: asyncio.Queue):
    async with websockets.connect(uri, **CONNECT_KW) as ws:
        _p("✅ [WS-EMIT] Connected.")
        _p("🟢 [WS-EMIT] Ready.")
        send_task = asyncio.create_task(_sender(ws, queue))
        recv_task = asyncio.create_task(_receiver(ws))
        try:
            done, pending = await asyncio.wait({send_task, recv_task}, return_when=asyncio.FIRST_EXCEPTION)
            for t in pending:
                t.cancel()
            for t in done:
                exc = t.exception()
                if exc:
                    raise exc
        finally:
            for t in (send_task, recv_task):
                if t:
                    t.cancel()
                    with suppress(asyncio.CancelledError):
                        await t


async def _run(uri: str):
    global _queue
    _queue = asyncio.Queue()
    _p("🚀 [WS-EMIT] Starting ...")

    backoff = 1
    while not _stop_evt.is_set():
        _p("⏳ [WS-EMIT] Waiting ...")
        try:
            await _session(uri, _queue)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 10)
        except (ConnectionRefusedError, OSError) as e:
            _p(f"🔌 [WS-EMIT] Disconnected: code=? reason={e}")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 10)
        except (ConnectionClosedOK, ConnectionClosedError):
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 10)
        except asyncio.CancelledError:
            break
        except Exception as e:
            _p(f"🔌 [WS-EMIT] Disconnected: unexpected: {e}")
            await asyncio.sleep(1)
            backoff = min(backoff * 2, 10)
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


def send(payload: dict):
    if _loop is None or _queue is None:
        return
    _loop.call_soon_threadsafe(_queue.put_nowait, payload)


def stop():
    global _thread
    if not _thread:
        return
    _stop_evt.set()
    if _loop and _queue:
        with suppress(Exception):
            _loop.call_soon_threadsafe(_queue.put_nowait, None)
    _thread.join(timeout=3)
    _thread = None
