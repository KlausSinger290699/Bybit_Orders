# ws_client.py
import asyncio, json, time, random
from contextlib import suppress
import websockets
from log_uniform import UniformLogger

URI = "ws://127.0.0.1:8765"
TF_CHOICES = ["1", "5", "15", "30"]
CONNECT_KW = dict(ping_interval=20, ping_timeout=20, close_timeout=1)

log = UniformLogger("CLIENT")

def make_event():
    tf = random.choice(TF_CHOICES)
    now = int(time.time())
    return {"source":"test","side":random.choice(["bull","bear"]),"status":"?","tf":tf,"start":now,"end":now+int(tf)*60}

async def stdin_reader(queue: asyncio.Queue):
    while True:
        line = await asyncio.to_thread(input)
        await queue.put(line)

async def session(ws, in_q: asyncio.Queue) -> bool:
    log.connected()
    log.ready()
    log.prompt()
    print()

    while True:
        input_task  = asyncio.create_task(in_q.get())
        closed_task = asyncio.create_task(ws.wait_closed())
        done, _ = await asyncio.wait({input_task, closed_task}, return_when=asyncio.FIRST_COMPLETED)

        if closed_task in done:
            input_task.cancel()
            with suppress(asyncio.CancelledError):
                await input_task
            log.disconnected(ws.close_code, getattr(ws, "close_reason", ""))
            return False

        closed_task.cancel()
        with suppress(asyncio.CancelledError):
            await closed_task

        user = input_task.result().strip().lower()
        if user == "q":
            with suppress(Exception):
                await ws.close(code=1000, reason="client quits")
            log.disconnected(1000, "client quits")
            return True

        evt = make_event()
        wire = json.dumps(evt)
        try:
            await ws.send(wire)
            log.sent_summary(evt["side"], evt["tf"], evt["status"])
            log.sent_wire(wire)
            reply = await ws.recv()
            log.got_reply(reply)
        except websockets.ConnectionClosedOK as ex:
            log.disconnected(getattr(ex,"code",None), getattr(ex,"reason",""))
            return False
        except websockets.ConnectionClosedError as ex:
            log.disconnected(getattr(ex,"code",None), getattr(ex,"reason",""))
            return False
        except (ConnectionResetError, OSError) as ex:
            log.disconnected(None, str(ex))
            return False

async def run():
    log.starting()
    in_q = asyncio.Queue()
    reader_task = asyncio.create_task(stdin_reader(in_q))
    backoff = 1
    waiting_printed = False

    try:
        while True:
            if not waiting_printed:
                log.waiting()
                waiting_printed = True

            try:
                async with websockets.connect(URI, **CONNECT_KW) as ws:
                    backoff = 1
                    waiting_printed = False
                    if await session(ws, in_q):
                        break
            except (ConnectionRefusedError, OSError):
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 10)
            except KeyboardInterrupt:
                log.stopped_by_user()
                break
            else:
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 10)
    finally:
        reader_task.cancel()
        with suppress(asyncio.CancelledError):
            await reader_task

if __name__ == "__main__":
    asyncio.run(run())
