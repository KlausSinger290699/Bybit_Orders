import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional
from playwright.async_api import async_playwright

# --- CONFIG ---
PREFIX = "[AGGR INDICATOR]"
URL = "https://charts.aggr.trade/koenzv4"
PROFILE_DIR = r"C:\Users\Anwender\PlaywrightProfiles\aggr"
SAVE_PATH = Path("threads.json")


# --- DATA MODEL ---

# --- add this helper somewhere above on_console ---
def is_divergence_event(payload: dict) -> bool:
    # Only accept normalized indicator events our receiver prints
    if not isinstance(payload, dict):
        return False
    if payload.get("v") != 1:
        return False
    if payload.get("source") != "aggr/indicator":
        return False
    # Must have thread metadata
    if not isinstance(payload.get("thread_id"), str):
        return False
    if not isinstance(payload.get("sequence"), int):
        return False
    # Side/status are expected too
    if not isinstance(payload.get("side"), str):
        return False
    if not isinstance(payload.get("status"), str):
        return False
    return True

class DivergenceEvent:
    """Immutable event wrapper."""
    def __init__(self, data: dict):
        self.data = data

    @property
    def thread_id(self) -> str:
        return self.data.get("thread_id", "unknown")

    @property
    def sequence(self) -> int:
        return self.data.get("sequence", 0)

    @property
    def side(self) -> str:
        return self.data.get("side", "?")

    @property
    def status(self) -> str:
        return self.data.get("status", "?")

    def to_dict(self) -> dict:
        return dict(self.data)


class Thread:
    """Represents a divergence thread (✅ confirmed + ❔ potentials)."""
    def __init__(self, thread_id: str, side: str):
        self.thread_id = thread_id
        self.side = side
        self._events: List[DivergenceEvent] = []

    def add_event(self, event: DivergenceEvent):
        self._events.append(event)
        self._events.sort(key=lambda e: e.sequence)

    @property
    def events(self) -> List[DivergenceEvent]:
        return list(self._events)

    @property
    def latest(self) -> Optional[DivergenceEvent]:
        return self._events[-1] if self._events else None

    def to_dict(self) -> dict:
        return {
            "thread_id": self.thread_id,
            "side": self.side,
            "events": [e.to_dict() for e in self._events],
        }


class ThreadStore:
    """Central store for all divergence threads (ordered print per sequence)."""
    def __init__(self):
        self._threads: Dict[str, Thread] = {}
        self._last_seq: Optional[int] = None
        self._cur_seq: Optional[int] = None
        self._buf: List[dict] = []  # buffer of raw event dicts for current sequence

    @staticmethod
    def fmt_price(p):
        if isinstance(p, (int, float)):
            return f"{int(round(p))}"  # no decimals
        return "?"

    @staticmethod
    def fmt_tf(sec):
        table = {
            60:"1m", 120:"2m", 180:"3m", 300:"5m", 600:"10m", 900:"15m",
            1200:"20m", 1800:"30m", 3600:"1h", 7200:"2h", 14400:"4h",
            21600:"6h", 43200:"12h", 86400:"1d"
        }
        return table.get(sec, f"{sec}s" if isinstance(sec, int) else "?")

    def _extract_L1_L2(self, data: dict):
        piv = data.get("pivots") or {}
        l1 = data.get("L1") or piv.get("L1") or {}
        l2 = data.get("L2") or piv.get("L2") or {}
        return l1, l2

    def _flush_current_sequence(self):
        if not self._buf or self._cur_seq is None:
            return

        # sort buffered events by first pivot time (older low) ascending
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
            l1p = self.fmt_price(l1.get("price"))
            l2p = self.fmt_price(l2.get("price"))
            tf  = data.get("tf_label") or self.fmt_tf(data.get("tf_sec"))

            print(f"{status_icon} {side_icon} | {l1p}-{l2p} ({tf})")

        self._last_seq = self._cur_seq
        self._cur_seq = None

    def add_event(self, data: dict):
        event = DivergenceEvent(data)
        tid = event.thread_id

        # ensure thread bucket exists & store event
        if tid not in self._threads:
            self._threads[tid] = Thread(thread_id=tid, side=event.side)
        self._threads[tid].add_event(event)

        seq = event.sequence  # existing sequence value you already have

        # if the sequence changed, flush previous and start a new buffer
        if self._cur_seq is None:
            self._cur_seq = seq
        elif seq != self._cur_seq:
            self._flush_current_sequence()
            self._cur_seq = seq

        # buffer this event for ordered printing
        self._buf.append(data)

    def get_thread(self, thread_id: str) -> Optional[Thread]:
        return self._threads.get(thread_id)

    def all_threads(self) -> List[Thread]:
        return list(self._threads.values())

    def to_dict(self) -> dict:
        return {tid: thread.to_dict() for tid, thread in self._threads.items()}

    def save_json(self, path: Path):
        # ensure the latest (possibly incomplete) sequence is printed before saving
        self._flush_current_sequence()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        print(f"💾 Saved {len(self._threads)} threads to {path}")

        print(f"💾 Saved {len(self._threads)} threads to {path}")



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


# --- MAIN LOOP ---

async def main():
    Path(PROFILE_DIR).mkdir(parents=True, exist_ok=True)
    store = ThreadStore()

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False
        )
        page = await context.new_page()

        # --- replace your on_console with this ---
        def on_console(msg):
            text = getattr(msg, "text", msg)
            ok, payload = extract_payload(str(text))
            if not ok:
                return
            if isinstance(payload, dict) and is_divergence_event(payload):
                store.add_event(payload)
            # else: silently ignore non-event logs (e.g., {"msg":"bus ready"})

        page.on("console", on_console)
        await page.goto(URL)
        print("🟢 Listening… prefix:", PREFIX)

        try:
            while True:
                await asyncio.sleep(60)
                store.save_json(SAVE_PATH)
        except KeyboardInterrupt:
            print("💾 Saving before exit...")
            store.save_json(SAVE_PATH)

if __name__ == "__main__":
    asyncio.run(main())
