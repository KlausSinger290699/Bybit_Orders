# bull_div_reader.py (sync Playwright)  — with WebSocket emitter bridge
import json
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from pathlib import Path
from playwright.sync_api import sync_playwright
# from pyee import EventEmitter  # no longer needed for WS path
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.SendData import ws_emit_bridge 


# bus = EventEmitter()  # no longer used

# --- CONFIG ---
PREFIX = "[AGGR INDICATOR]"
URL = "https://charts.aggr.trade/koenzv4"
PROFILE_DIR = r"C:\Users\Anwender\PlaywrightProfiles\aggr"
WS_URI = "ws://127.0.0.1:8765"  # NEW: where to send payloads

# Visual layout constants for the sequence header/footer
SEQ_TARGET_INNER = 58  # target inner width between the corners (tweak to taste)


# --- HELPERS -----------------------------------------------------------------

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
        60: "1m", 120: "2m", 180: "3m", 300: "5m", 600: "10m", 900: "15m",
        1200: "20m", 1800: "30m", 3600: "1h", 7200: "2h", 14400: "4h",
        21600: "6h", 43200: "12h", 86400: "1d"
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


# --- Unicode styling helpers -------------------------------------------------

def to_bold_unicode(s: str) -> str:
    """
    Convert ASCII letters/digits in s to mathematical bold unicode equivalents.
    Leaves other chars as-is (including emoji and box-drawing).
    """
    out = []
    for ch in s:
        o = ord(ch)
        if 0x41 <= o <= 0x5A:  # A-Z
            out.append(chr(0x1D400 + (o - 0x41)))
        elif 0x61 <= o <= 0x7A:  # a-z
            out.append(chr(0x1D41A + (o - 0x61)))
        elif 0x30 <= o <= 0x39:  # 0-9
            out.append(chr(0x1D7CE + (o - 0x30)))
        else:
            out.append(ch)
    return "".join(out)


def seq_bars(seq_no: int, tf_label: str):
    """
    Build the Option A bars with bold text so the tone matches the heavy lines.

    Returns (top_bar, bottom_bar).
    Example top: ┏━━ 📌 𝗦𝗲𝗾𝘂𝗲𝗻𝗰𝗲 ＃𝟭 — 𝟭𝟱𝗺 ━━━━━…┓
            bot: ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━…┛
    """
    # Bold the words/numbers; make '#' fullwidth so it doesn't look lighter
    title = f"📌 {to_bold_unicode('Sequence')} \uFF03{to_bold_unicode(str(seq_no))} — {to_bold_unicode(tf_label)} "

    left_prefix = "━━ "  # sits after the opening corner
    inner_base = left_prefix + title
    # fill with heavy lines to a nice even width
    fill_len = max(0, SEQ_TARGET_INNER - len(inner_base))
    inner_line = inner_base + ("━" * fill_len)

    top = f"┏{inner_line}┓"
    bottom = f"┗{'━' * len(inner_line)}┛"
    return top, bottom


# --- PRINTER (sequence-buffered, ordered by L1.time) ------------------------

# --- PRINTER (display-only; no selection, no WS send) ------------------------

class Printer:
    """Pretty console output for divergence events.
    Responsibilities:
      - Buffer events per sequence id.
      - Sort buffered events by L1.time for readability.
      - Render a compact list under a bold header/footer.
    Non-responsibilities (moved elsewhere):
      - Building payloads
      - Deciding tradability
      - Sending over WebSocket
      - Any strategy logic
    """

    def __init__(self):
        self._cur_seq: Optional[int] = None
        self._buf: list[dict] = []  # raw event dicts (already validated upstream)

    def _flush(self):
        if not self._buf or self._cur_seq is None:
            return

        def l1_time(ev: dict):
            l1, _ = extract_L1_L2(ev)
            t = l1.get("time")
            return t if isinstance(t, (int, float)) else float("inf")

        batch = sorted(self._buf, key=l1_time)
        self._buf.clear()

        # Header/footer bars
        tf_label = (batch[-1].get("tf_label") or fmt_tf(batch[-1].get("tf_sec"))) if batch else "?"
        top_bar, bottom_bar = seq_bars(self._cur_seq, tf_label)
        print("\n" + top_bar)

        # One line per event
        for ev in batch:
            side = ev.get("side", "?")
            side_icon = "🟢" if side == "bull" else "🔴" if side == "bear" else "⚪"
            status_icon = ev.get("status", "?")

            l1, l2 = extract_L1_L2(ev)
            l1p = fmt_price(l1.get("price"))
            l2p = fmt_price(l2.get("price"))

            print(f"{status_icon} {side_icon} | {l1p}-{l2p}")

        print(bottom_bar)
        self._cur_seq = None

    def add_event(self, ev: dict):
        """Append an event to the current sequence block; flush on sequence change."""
        seq = ev.get("sequence")
        if self._cur_seq is None:
            self._cur_seq = seq
        elif seq != self._cur_seq:
            self._flush()
            self._cur_seq = seq
        self._buf.append(ev)

    def flush_now(self):
        """Force flush (e.g., on shutdown)."""
        self._flush()


# --- STRATEGY ENGINE (entry detection) --------------------------------------

@dataclass(frozen=True)
class EngineConfig:
    max_pivot_time_diff_sec: int = 0  # exact match for now


class StrategyEngine:
    """
    Detects: A previous bull event (✅ or ❔) whose L2 is the same pivot as the
    next bull ❔ event's L1 → print entry instruction.
    """
    def __init__(self, cfg: EngineConfig = EngineConfig()):
        self.cfg = cfg
        self._l2_index: Dict[int, dict] = {}        # pivot_time -> prior event
        self._printed: set[str] = set()             # de-dupe "prev->curr"

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
        if ev.get("status") not in ("✅", "❔"):
            return
        _l1, l2 = extract_L1_L2(ev)
        t = self._safe_int(l2.get("time"))
        if t is not None:
            self._l2_index[t] = ev

    def _match_prev_l2_with_curr_l1(self, curr: dict) -> Optional[dict]:
        if curr.get("side") != "bull":
            return None
        if curr.get("status") != "❔":
            return None
        l1, _ = extract_L1_L2(curr)
        t = self._safe_int(l1.get("time"))
        return self._l2_index.get(t) if t is not None else None

    def on_event(self, ev: dict):
        prev = self._match_prev_l2_with_curr_l1(ev)
        if prev is not None:
            entry_key = f"{prev.get('thread_id','?')}->{ev.get('thread_id','?')}"
            if entry_key not in self._printed:
                self._printed.add(entry_key)
                self._print_entry(prev, ev)
        self._store_prior_bull_l2(ev)

    def _print_entry(self, prev: dict, curr: dict):
        curr_l1, _ = extract_L1_L2(curr)
        _prev_l1, prev_l2 = extract_L1_L2(prev)
        sl_price = prev_l2.get("price")
        sl_ts = prev_l2.get("time")
        tf_label = curr.get("tf_label") or fmt_tf(curr.get("tf_sec"))

        print("\n🟢📣  ENTRY SIGNAL (Bull)")
        print("   ├─ Rule: (prev ✅/❔) L2 == (next ❔) L1")
        print(f"   ├─ TF: {tf_label}")
        print(f"   ├─ Prev Thread: {prev.get('thread_id')}")
        print(f"   ├─ Curr Thread: {curr.get('thread_id')}")
        print(f"   ├─ L2(prev) == L1(curr): time={sl_ts}  price={fmt_price(sl_price)}")
        print("   └─ Action: enter trade with 1% account risk with pyramiding; "
              "stop loss on L1 (the previous L2).")


# --- MAIN LOOP (sync, callback + non-blocking idle) -------------------------

def main():
    Path(PROFILE_DIR).mkdir(parents=True, exist_ok=True)
    printer = Printer()
    engine = StrategyEngine()

    # Start background WS emitter
    ws_emit_bridge.start(WS_URI)  # NEW

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False
        )
        page = context.new_page()

        # 1) ATTACH LISTENER *BEFORE* NAVIGATION (prevents missing early logs)
        def on_console(msg):
            try:
                raw = msg.text()  # sync API: method, not property
            except Exception:
                raw = str(msg)

            ok, payload = extract_payload(raw)
            if not ok:
                return
            if isinstance(payload, dict) and is_divergence_event(payload):
                # Strategy first (real-time reactions), then pretty print batches
                engine.on_event(payload)
                printer.add_event(payload)

        page.on("console", on_console)

        # 2) Now navigate
        page.goto(URL)
        print("🟢 Listening… prefix:", PREFIX)

        # 3) Keep process alive without blocking Playwright's event pump
        try:
            while True:
                page.wait_for_timeout(5_000)  # yields; lets console events fire
                # Optional: periodically flush current block if you want:
                # printer.flush_now()
        except KeyboardInterrupt:
            printer.flush_now()
        finally:
            for pge in list(context.pages):
                try: pge.close()
                except Exception: pass
            try: context.close()
            except Exception: pass
            # Stop background WS emitter
            ws_emit_bridge.stop()  # NEW


if __name__ == "__main__":
    main()
