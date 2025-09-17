import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

# --- CONFIG ---
PREFIX = "[AGGR INDICATOR]"
URL = "https://charts.aggr.trade/koenzv4"
PROFILE_DIR = r"C:\Users\Anwender\PlaywrightProfiles\aggr"


# --- HELPERS ---

def extract_payload(console_text: str):
    """Extract JSON payload after [AGGR INDICATOR] prefix."""
    if PREFIX not in console_text:
        return False, None
    after = console_text.split(PREFIX, 1)[1].strip()
    if after.startswith("{") or after.startswith("["):
        try:
            return True, json.loads(after)
        except json.JSONDecodeError:
            return True, after
    return True, after

def is_divergence_event(payload: dict) -> bool:
    # Only accept normalized indicator events our receiver prints
    if not isinstance(payload, dict):
        return False
    if payload.get("v") != 1:
        return False
    if payload.get("source") != "aggr/indicator":
        return False
    if not isinstance(payload.get("thread_id"), str):
        return False
    if not isinstance(payload.get("sequence"), int):
        return False
    if not isinstance(payload.get("side"), str):
        return False
    if not isinstance(payload.get("status"), str):
        return False
    return True


# --- PRINTER (sequence-buffered, ordered by L1.time) ---

class Printer:
    def __init__(self):
        self._cur_seq = None
        self._buf = []  # list of raw event dicts

    @staticmethod
    def _fmt_price(p):
        if isinstance(p, (int, float)):
            return f"{int(round(p))}"
        return "?"

    @staticmethod
    def _fmt_tf(sec):
        table = {
            60:"1m", 120:"2m", 180:"3m", 300:"5m", 600:"10m", 900:"15m",
            1200:"20m", 1800:"30m", 3600:"1h", 7200:"2h", 14400:"4h",
            21600:"6h", 43200:"12h", 86400:"1d"
        }
        return table.get(sec, f"{sec}s" if isinstance(sec, int) else "?")

    @staticmethod
    def _extract_L1_L2(data: dict):
        piv = data.get("pivots") or {}
        l1 = data.get("L1") or piv.get("L1") or {}
        l2 = data.get("L2") or piv.get("L2") or {}
        return l1, l2

    def _flush(self):
        if not self._buf or self._cur_seq is None:
            return

        def l1_time(ev):
            l1, _ = self._extract_L1_L2(ev)
            t = l1.get("time")
            return t if isinstance(t, (int, float)) else float("inf")

        batch = sorted(self._buf, key=l1_time)
        self._buf.clear()

        print(f"\n─────────────── 📌 Sequence #{self._cur_seq} ───────────────")
        for data in batch:
            side = data.get("side", "?")
            side_icon = "🟢" if side == "bull" else "🔴"
            status_icon = data.get("status", "?")
            l1, l2 = self._extract_L1_L2(data)
            l1p = self._fmt_price(l1.get("price"))
            l2p = self._fmt_price(l2.get("price"))
            tf  = data.get("tf_label") or self._fmt_tf(data.get("tf_sec"))
            print(f"{status_icon} {side_icon} | {l1p}-{l2p} ({tf})")

        self._cur_seq = None

    def add_event(self, data: dict):
        seq = data.get("sequence")

        if self._cur_seq is None:
            self._cur_seq = seq
        elif seq != self._cur_seq:
            # sequence changed → flush previous block, start new
            self._flush()
            self._cur_seq = seq

        self._buf.append(data)

    def flush_now(self):
        self._flush()


# --- MAIN LOOP ---

async def main():
    Path(PROFILE_DIR).mkdir(parents=True, exist_ok=True)
    printer = Printer()

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False
        )
        page = await context.new_page()

        def on_console(msg):
            text = getattr(msg, "text", msg)
            ok, payload = extract_payload(str(text))
            if not ok:
                return
            if isinstance(payload, dict) and is_divergence_event(payload):
                printer.add_event(payload)
            # else: ignore non-event logs silently

        page.on("console", on_console)
        await page.goto(URL)
        print("🟢 Listening… prefix:", PREFIX)

        try:
            while True:
                await asyncio.sleep(60)
                # optional: flush the current block periodically if you want to see it even
                # when the sequence hasn't changed for a while:
                # printer.flush_now()
        except KeyboardInterrupt:
            printer.flush_now()

if __name__ == "__main__":
    asyncio.run(main())
