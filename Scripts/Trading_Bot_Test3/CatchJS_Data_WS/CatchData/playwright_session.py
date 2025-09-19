# CatchData/playwright_session.py
from pathlib import Path
from collections import defaultdict
from playwright.sync_api import sync_playwright
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.z_Helpers import utils

PROFILE_DIR = Path(r"C:\Users\Anwender\PlaywrightProfiles\aggr")
URL = "https://charts.aggr.trade/koenzv4"
PREFIX = "[AGGR INDICATOR]"

def iter_blocks():
    """
    Stream complete blocks forever. Each yielded item is a list[dict] of all events
    that share the same global sequence number. No duplicates.
    """
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
        )
        page = context.new_page()

        # sequence -> list of events
        buffers: dict[int, list] = defaultdict(list)
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
                # look for the next sequence after last_yielded_seq
                ready = sorted(
                    s for s in buffers.keys()
                    if (last_yielded_seq is None or s > last_yielded_seq)
                )

                if ready:
                    s = ready[0]
                    block = buffers.pop(s, [])
                    last_yielded_seq = s

                    # keep memory small: drop old sequences
                    for k in list(buffers.keys()):
                        if k <= last_yielded_seq - 3:
                            buffers.pop(k, None)

                    if block:
                        yield block
                else:
                    page.wait_for_timeout(100)

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
