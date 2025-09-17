# ws_emit_bridge.py
import json
import threading
import asyncio
from contextlib import suppress
from typing import Optional

import websockets
from websockets import ConnectionClosedOK, ConnectionClosedError

# --- logging (same style as your emitter/receiver) ---------------------------
try:
    from log_uniform import UniformLogger
    log = UniformLogger("WS-EMIT")
except Exception:  # fallback
    class _Bare:
        def starting(self): print("🚀 [WS-EMIT] Starting ...")
        def waiting(self): print("⏳ [WS-EMIT] Waiting ...")
        def connected(self): print("✅ [WS-EMIT] Connected.")
        def ready(self): print("🟢 [WS-EMIT] Ready.")
        def disconnected(self, code, reason): print(f"🔌 [WS-EMIT] Disconnected: code={code} reason={reason}")
        def sent_wire(self, wire): print(f"📤 [WS-EMIT] Sent (json)   : {wire}")
        def got_reply(self, reply): print(f"📨 [WS-EMIT] Got reply (raw): {reply}\n")
        def stopped_by_user(self): print("\n🟥 [WS-EMIT] Stopped by user.")
    log = _Bare()

# --- config mirrors ----------------------------------------------------------
CONNECT_KW = dict(ping_interval=20, ping_timeout=20, close_timeout=1)

# --- internal globals --------------------------------------------------------
_URI: Optional[str] = None
_loop: Optional[asyncio.AbstractEventLoop] = None
_thread: Optional[threading.Thread] = None
_queue: Optional[asyncio.Queue] = None
_stop_evt = threading.Event()

# --- core tasks --------------------------------------------------------------
async def _sender(ws, queue: asyncio.Queue):
    """Drain the queue and send payloads."""
    while not _stop_evt.is_set():
        item = await queue.get()
        # allow stop nudge
        if item is None or item is _stop_evt:
            break
        wire = json.dumps(item)
        await ws.send(wire)
        log.sent_wire(wire)

async def _receiver(ws):
    """Read replies (to match your emitter’s behavior)."""
    try:
        async for msg in ws:
            log.got_reply(msg)
    except ConnectionClosedOK as e:
        log.disconnected(e.code, getattr(e, "reason", ""))
        raise
    except ConnectionClosedError as e:
        log.disconnected(e.code, getattr(e, "reason", ""))
        raise

async def _session(uri: str, queue: asyncio.Queue):
    """One connection session; returns when disconnected."""
    log.connected()
    log.ready()

    send_task = recv_task = None
    try:
        async with websockets.connect(uri, **CONNECT_KW) as ws:
            send_task = asyncio.create_task(_sender(ws, queue))
            recv_task = asyncio.create_task(_receiver(ws))

            done, pending = await asyncio.wait(
                {send_task, recv_task},
                return_when=asyncio.FIRST_EXCEPTION
            )
            for t in pending:
                t.cancel()
            for t in done:
                # surface exceptions to outer loop
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
    """Reconnect loop with exponential backoff (like your emitter)."""
    global _queue
    _queue = asyncio.Queue()
    log.starting()

    backoff = 1
    while not _stop_evt.is_set():
        log.waiting()
        try:
            await _session(uri, _queue)
            # if session ends cleanly, try reconnect (after small backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 10)
        except (ConnectionRefusedError, OSError) as e:
            log.disconnected(None, str(e))
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 10)
        except (ConnectionClosedOK, ConnectionClosedError) as e:
            # closed by peer; reconnect with backoff
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 10)
        except asyncio.CancelledError:
            break
        except Exception as e:
            # unexpected — don’t crash, retry soon
            log.disconnected(None, f"unexpected: {e}")
            await asyncio.sleep(1)
            backoff = min(backoff * 2, 10)

    # drain/close
    try:
        await _queue.put(None)
    except Exception:
        pass

# --- public API --------------------------------------------------------------
def start(uri: str):
    """Start background emitter (idempotent)."""
    global _URI, _loop, _thread
    if _thread and _thread.is_alive():
        return
    _URI = uri
    _stop_evt.clear()

    def _thread_target():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_run(_URI))
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    _thread = threading.Thread(target=_thread_target, name="ws-emit-bridge", daemon=True)
    _thread.start()

def send(payload: dict):
    """Queue a payload to be sent (thread-safe, non-blocking)."""
    global _loop, _queue
    if _queue is None:
        return
    # push without blocking caller
    # (we don't require the result; best-effort enqueue)
    try:
        # fast path if we're already in the bridge thread loop
        if asyncio.get_event_loop().is_running():
            # likely not the bridge loop; use threadsafe anyway
            pass
    except RuntimeError:
        pass
    # put_nowait on queue in its loop
    # use call_soon_threadsafe to avoid awaiting
    loop = None
    for t in threading.enumerate():
        if t.name == "ws-emit-bridge":
            loop = _loop  # not directly exposed, but safe to use global
            break
    if loop is None:
        # fall back: try to schedule via any known loop (if we captured it)
        loop = _loop
    if loop:
        loop.call_soon_threadsafe(_queue.put_nowait, payload)

def stop():
    """Stop the bridge and wait briefly."""
    if not _thread:
        return
    _stop_evt.set()
    # nudge queue so sender can exit
    if _loop and _queue:
        try:
            _loop.call_soon_threadsafe(_queue.put_nowait, None)
        except Exception:
            pass
    _thread.join(timeout=3)
