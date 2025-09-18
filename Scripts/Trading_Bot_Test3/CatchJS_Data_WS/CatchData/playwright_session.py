# CatchData/playwright_session.py
from pathlib import Path
from collections import defaultdict, deque
from playwright.sync_api import sync_playwright
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.CatchData import utils

PROFILE_DIR = Path(r"C:\Users\Anwender\PlaywrightProfiles\aggr")
URL = "https://charts.aggr.trade/koenzv4"
PREFIX = "[AGGR INDICATOR]"
EVENTS_PER_SEQUENCE = 4  # must match printer

def iter_blocks():
    """
    Stream complete blocks forever. Each yielded item is a list[dict] of length
    EVENTS_PER_SEQUENCE for the next sequence in ascending order. No duplicates.
    """
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
        )
        page = context.new_page()

        # seq -> deque of most-recent events for that seq
        buffers: dict[int, deque] = defaultdict(lambda: deque(maxlen=EVENTS_PER_SEQUENCE))
        last_yielded_seq: int | None = None

        def _on_console(msg):
            try:
                raw_text = msg.text()
            except Exception:
                raw_text = str(msg)

            ok, payload = utils.extract_payload(raw_text, PREFIX)
            if not ok or not isinstance(payload, dict):
                return
            if not utils.is_divergence_event(payload):
                return

            seq = payload.get("sequence")
            if isinstance(seq, int):
                buffers[seq].append(payload)

        page.on("console", _on_console)

        try:
            page.goto(URL)
            print("🟢 Listening… prefix:", PREFIX)
            # sanity probe (ignored by is_divergence_event)
            page.evaluate(f"console.log('{PREFIX} __probe__ console-wired')")

            while True:
                # choose the *next* sequence after last_yielded_seq that is full
                ready = sorted(s for s in buffers.keys()
                               if len(buffers[s]) >= EVENTS_PER_SEQUENCE
                               and (last_yielded_seq is None or s > last_yielded_seq))

                if ready:
                    s = ready[0]
                    block = list(buffers[s])[:EVENTS_PER_SEQUENCE]
                    last_yielded_seq = s

                    # optional: drop older seq buffers to keep memory small
                    for k in list(buffers.keys()):
                        if k <= last_yielded_seq - 3:  # keep a small tail
                            buffers.pop(k, None)

                    yield block
                else:
                    page.wait_for_timeout(100)  # let events pump

        finally:
            try:
                context.close()
            except Exception:
                pass

def get_raw():
    """
    Backward-compatible: return just the next full block once.
    """
    for block in iter_blocks():
        return block
