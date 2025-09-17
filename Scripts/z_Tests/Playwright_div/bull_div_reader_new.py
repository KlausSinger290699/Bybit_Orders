import asyncio
import json
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
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


def fmt_tf(sec):
    table = {
        60:"1m", 120:"2m", 180:"3m", 300:"5m", 600:"10m", 900:"15m",
        1200:"20m", 1800:"30m", 3600:"1h", 7200:"2h", 14400:"4h",
        21600:"6h", 43200:"12h", 86400:"1d"
    }
    return table.get(sec, f"{sec}s" if isinstance(sec, int) else "?")


def extract_L1_L2(data: dict) -> Tuple[dict, dict]:
    piv = data.get("pivots") or {}
    l1 = data.get("L1") or piv.get("L1") or {}
    l2 = data.get("L2") or piv.get("L2") or {}
    return l1, l2


def fmt_price(p):
    if isinstance(p, (int, float)):
        return f"{int(round(p))}"
    return "?"


# --- PRINTER (sequence-buffered, ordered by L1.time) ---

class Printer:
    def __init__(self):
        self._cur_seq = None
        self._buf = []  # list of raw event dicts

    def _flush(self):
        if not self._buf or self._cur_seq is None:
            return

        def l1_time(ev):
            l1, _ = extract_L1_L2(ev)
            t = l1.get("time")
            return t if isinstance(t, (int, float)) else float("inf")

        batch = sorted(self._buf, key=l1_time)
        self._buf.clear()

        print(f"\n─────────────── 📌 Sequence #{self._cur_seq} ───────────────")
        for data in batch:
            side = data.get("side", "?")
            side_icon = "🟢" if side == "bull" else "🔴"
            status_icon = data.get("status", "?")
            l1, l2 = extract_L1_L2(data)
            l1p = fmt_price(l1.get("price"))
            l2p = fmt_price(l2.get("price"))
            tf  = data.get("tf_label") or fmt_tf(data.get("tf_sec"))
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


# --- STRATEGY ENGINE (entry detection) ---

@dataclass(frozen=True)
class EngineConfig:
    # For future extension: allow time vicinity (e.g., <= 1h when tf=15m).
    # For now we require exact pivot match.
    max_pivot_time_diff_sec: int = 0


class StrategyEngine:
    """
    Detects: A previous bull event (✅ or ❔) whose L2 is the same pivot as the
    next bull ❔ event's L1 → print entry instruction.
    """
    def __init__(self, cfg: EngineConfig = EngineConfig()):
        self.cfg = cfg
        # Map of pivot_time -> prior event that ended on that pivot as L2
        self._l2_index: Dict[int, dict] = {}
        # De-dupe printed entries: key = f"{prev_thread}->{curr_thread}"
        self._printed: set[str] = set()

    @staticmethod
    def _safe_int(x) -> Optional[int]:
        if isinstance(x, (int, float)):
            return int(x)
        try:
            return int(x)
        except Exception:
            return None

    def _store_prior_bull_l2(self, ev: dict):
        if ev.get("side") != "bull":
            return
        status = ev.get("status")
        if status not in ("✅", "❔"):
            return
        _l1, l2 = extract_L1_L2(ev)
        t = self._safe_int(l2.get("time"))
        if t is None:
            return
        # Index by exact time (extend to vicinity later)
        self._l2_index[t] = ev

    def _match_prev_l2_with_curr_l1(self, curr: dict) -> Optional[dict]:
        if curr.get("side") != "bull":
            return None
        if curr.get("status") != "❔":  # next must be potential
            return None
        l1, _l2 = extract_L1_L2(curr)
        t = self._safe_int(l1.get("time"))
        if t is None:
            return None

        # Exact match for now; extend later using tolerance
        prev = self._l2_index.get(t)
        return prev

    def on_event(self, ev: dict):
        """
        Feed each event here (already normalized from the receiver).
        Order is already roughly sorted; we also handle out-of-order gracefully.
        """
        # Try to match current event (as "next ❔") to a previous "✅/❔" L2
        prev = self._match_prev_l2_with_curr_l1(ev)
        if prev is not None:
            entry_key = f"{prev.get('thread_id','?')}->{ev.get('thread_id','?')}"
            if entry_key not in self._printed:
                self._printed.add(entry_key)
                self._print_entry(prev, ev)

        # Regardless, if current event is a prior candidate (✅/❔ with L2), store it
        self._store_prior_bull_l2(ev)

    def _print_entry(self, prev: dict, curr: dict):
        # Stop loss on previous L2 (which equals current L1)
        curr_l1, _ = extract_L1_L2(curr)
        prev_l1, prev_l2 = extract_L1_L2(prev)

        sl_price = prev_l2.get("price")
        sl_ts = prev_l2.get("time")
        tf_label = curr.get("tf_label") or fmt_tf(curr.get("tf_sec"))

        # Be explicit and readable in console:
        print("\n🟢📣  ENTRY SIGNAL (Bull)")
        print("   ├─ Rule: (prev ✅/❔) L2 == (next ❔) L1")
        print(f"   ├─ TF: {tf_label}")
        print(f"   ├─ Prev Thread: {prev.get('thread_id')}")
        print(f"   ├─ Curr Thread: {curr.get('thread_id')}")
        print(f"   ├─ L2(prev) == L1(curr): time={sl_ts}  price={fmt_price(sl_price)}")
        print("   └─ Action: enter trade with 1% account risk with pyramiding; "
              "stop loss on L1 (the previous L2).")


# --- MAIN LOOP ---

async def main():
    Path(PROFILE_DIR).mkdir(parents=True, exist_ok=True)
    printer = Printer()
    engine = StrategyEngine()  # exact-match engine (ready to extend with tolerance later)

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
                # Strategy first (real-time reactions), then pretty print batches
                engine.on_event(payload)
                printer.add_event(payload)
            # else: ignore non-event logs silently

        page.on("console", on_console)
        await page.goto(URL)
        print("🟢 Listening… prefix:", PREFIX)

        try:
            while True:
                await asyncio.sleep(60)
                # Optionally flush the current Printer block periodically:
                # printer.flush_now()
        except KeyboardInterrupt:
            printer.flush_now()

if __name__ == "__main__":
    asyncio.run(main())
