from pathlib import Path
from collections import defaultdict
from time import monotonic
from playwright.sync_api import sync_playwright
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.z_Helpers import utils
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.PreprocessData import bybit_highs_lows_15m_batch as bybit

PROFILE_DIR = Path(r"C:\Users\Anwender\PlaywrightProfiles\aggr")
URL = "https://charts.aggr.trade/koenzv4"
PREFIX = "[AGGR INDICATOR]"

# ensure we warm Bybit exactly once (shows spinner + 'done ✅')
_BYBIT_WARMED = False

def iter_blocks_latest(debounce_ms: int = 80):
    """
    Stream ONLY the latest complete block.
    - Coalesces events by sequence.
    - Always jumps to the highest sequence (tail-drop).
    - Waits a tiny debounce so all events of that sequence arrive.
    """
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    debounce_s = debounce_ms / 1000.0

    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
        )
        page = context.new_page()

        buffers: dict[int, list] = defaultdict(list)  # seq -> list[evt]
        touched_at: dict[int, float] = {}            # seq -> last update time
        last_yielded: int | None = None

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
                touched_at[seq] = monotonic()

        page.on("console", _on_console)

        try:
            page.goto(URL)
            print("🟢 Listening… prefix:", PREFIX)

            # Load Bybit markets ONCE with spinner (right after the listening line)
            global _BYBIT_WARMED
            if not _BYBIT_WARMED:
                bybit.init_bybit_public()
                _BYBIT_WARMED = True

            page.evaluate(f"console.log('{PREFIX} __probe__ console-wired')")

            while True:
                if not buffers:
                    page.wait_for_timeout(50)
                    continue

                # Jump straight to the newest sequence we’ve seen.
                newest = max(buffers.keys())

                # Small debounce so all events for `newest` arrive
                # (especially when multiple threads emit for the same seq).
                if monotonic() - touched_at.get(newest, 0.0) < debounce_s:
                    page.wait_for_timeout(10)
                    continue

                # Yield only the newest and drop everything older.
                block = buffers.pop(newest, [])
                touched_at.pop(newest, None)
                # hard drop older sequences to avoid backlog
                for k in list(buffers.keys()):
                    if k < newest:
                        buffers.pop(k, None)
                        touched_at.pop(k, None)

                if block and newest != last_yielded:
                    last_yielded = newest
                    yield block
                else:
                    page.wait_for_timeout(10)

        finally:
            try:
                context.close()
            except Exception:
                pass

# Backward-compatible alias if you call iter_blocks() elsewhere:
iter_blocks = iter_blocks_latest
