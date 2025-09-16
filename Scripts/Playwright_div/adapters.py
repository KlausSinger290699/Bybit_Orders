# adapters.py
import asyncio, json, random
from pathlib import Path
from typing import Optional, Tuple
from core import DivergenceEvent, EventSource, EventSink, fmt_tf, pstr

PREFIX = "[AGGR INDICATOR]"

# =========================
# SINK: Console Printer
# =========================

class ConsolePrinter(EventSink):
    def __init__(self):
        self._cur_seq: Optional[int] = None
        self._buf: list[DivergenceEvent] = []

    def on_event(self, ev: DivergenceEvent) -> None:
        if self._cur_seq is None:
            self._cur_seq = ev.sequence
        elif ev.sequence != self._cur_seq:
            self._flush()
            self._cur_seq = ev.sequence
        self._buf.append(ev)

    def _flush(self):
        if not self._buf or self._cur_seq is None:
            return
        batch = sorted(self._buf, key=lambda e: (e.L1_time or 10**18))
        self._buf.clear()

        print(f"\n─────────────── 📌 Sequence #{self._cur_seq} ───────────────")
        for e in batch:
            side_icon = "🟢" if e.side == "bull" else "🔴"
            print(f"{e.status} {side_icon} | {pstr(e.L1_price)}-{pstr(e.L2_price)} ({fmt_tf(e.tf_sec)})")

        self._cur_seq = None

    def on_entry_signal(self, prev: DivergenceEvent, curr: DivergenceEvent) -> None:
        self._flush()
        print("\n🟢📣  ENTRY SIGNAL (Bull)")
        print("   ├─ Rule: (prev ✅/❔) L2 == (next ❔) L1")
        print(f"   ├─ TF: {fmt_tf(curr.tf_sec)}")
        print(f"   ├─ Prev Thread: {prev.thread_id}")
        print(f"   ├─ Curr Thread: {curr.thread_id}")
        print(f"   ├─ L2(prev) == L1(curr): time={prev.L2_time}  price={pstr(prev.L2_price)}")
        print("   └─ Action: enter trade with 1% account risk with pyramiding; "
              "stop loss on L1 (the previous L2).")

    def flush_now(self):
        self._flush()

# =========================
# SOURCE: Random Demo (no browser)
# =========================

class RandomDemoSource(EventSource):
    """
    Generates realistic-ish bull streams on 15m:
      - statuses from {✅, ❔, ❌} (weighted)
      - price drift
      - timestamps step by tf_sec
      - sometimes forces L2(prev) == L1(next ❔) to trigger entries
    """
    def __init__(
        self,
        *,
        tf_sec: int = 900,
        start_time: int = 1_726_000_000,
        start_price: float = 56000.0,
        n_events: int = 30,
        match_prob: float = 0.30,
        seed: Optional[int] = None,
    ):
        self.tf_sec = tf_sec
        self.t = start_time
        self.base_price = start_price
        self.n = n_events
        self.match_prob = max(0.0, min(1.0, match_prob))
        self.seq = 0
        self.last_prev_L2_time: Optional[int] = None
        self.last_prev_L2_price: Optional[float] = None
        self.force_match_next = False
        self.rng = random.Random(seed)

        self.status_choices = ["❔", "✅", "❌"]
        self.status_weights = [0.5, 0.35, 0.15]

    def _next_seq(self) -> int:
        self.seq += 1
        return self.seq

    def _jitter_price(self, base: float) -> float:
        pct = self.rng.uniform(-0.004, 0.004)  # +/-0.4%
        return max(100.0, base * (1.0 + pct))

    def _make_bull(self, status: str, l1_time: int, l2_time: int, l1_price: float, l2_price: float, hint: str) -> DivergenceEvent:
        seq = self._next_seq()
        tid = f"bull:{l1_time}-{l2_time}:{self.tf_sec}:{hint}"
        raw = {
            "v": 1,
            "source": "aggr/indicator",
            "tf_sec": self.tf_sec,
            "side": "bull",
            "status": status,
            "thread_id": tid,
            "pair_id": f"L1:{l1_time}|L2:{l2_time}",
            "sequence": seq,
            "L1": {"time": l1_time, "price": l1_price},
            "L2": {"time": l2_time, "price": l2_price},
        }
        ev = DivergenceEvent.from_raw(raw)
        return ev  # type: ignore

    async def events(self):
        for _ in range(self.n):
            # define a prev window
            l1_time = self.t
            l2_time = self.t + self.tf_sec

            l1_price = self._jitter_price(self.base_price * self.rng.uniform(0.999, 1.001))
            l2_price = self._jitter_price(l1_price * self.rng.uniform(0.998, 1.002))

            status = self.rng.choices(self.status_choices, weights=self.status_weights, k=1)[0]

            prev = self._make_bull(status, l1_time, l2_time, l1_price, l2_price, hint="prev")
            yield prev

            # maybe force next ❔ to match prev L2
            if status in ("✅", "❔") and self.rng.random() < self.match_prob:
                self.last_prev_L2_time = l2_time
                self.last_prev_L2_price = l2_price
                self.force_match_next = True
            else:
                self.force_match_next = False

            # often emit a follow-up ❔
            if self.rng.random() < 0.7:
                if self.force_match_next and self.last_prev_L2_time is not None:
                    next_l1_time = self.last_prev_L2_time
                    next_l1_price = self.last_prev_L2_price if self.last_prev_L2_price is not None else l2_price
                else:
                    next_l1_time = l2_time
                    next_l1_price = self._jitter_price(l2_price)

                next_l2_time = next_l1_time + self.tf_sec
                next_l2_price = self._jitter_price(next_l1_price)

                nxt = self._make_bull("❔", next_l1_time, next_l2_time, next_l1_price, next_l2_price, hint="next")
                yield nxt

            # advance for next loop
            self.t += self.tf_sec * self.rng.choice([1, 1, 2])  # sometimes skip bars
            self.base_price = self._jitter_price(self.base_price)
            await asyncio.sleep(0)

# =========================
# SOURCE: NDJSON replay
# =========================

class NDJSONReplaySource(EventSource):
    def __init__(self, path: str):
        self.path = path

    async def events(self):
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line: continue
                try:
                    raw = json.loads(line)
                except Exception:
                    continue
                ev = DivergenceEvent.from_raw(raw)
                if ev: yield ev
                await asyncio.sleep(0)

# =========================
# SOURCE: Playwright live (optional)
# =========================

def _extract_payload(console_text: str) -> Tuple[bool, object]:
    if PREFIX not in console_text: return (False, None)
    after = console_text.split(PREFIX, 1)[1].strip()
    if after.startswith("{") or after.startswith("["):
        try: return (True, json.loads(after))
        except json.JSONDecodeError: return (True, after)
    return (True, after)

class PlaywrightSource(EventSource):
    def __init__(self, url: str, profile_dir: str):
        self.url = url
        self.profile_dir = profile_dir

    async def events(self):
        try:
            from playwright.async_api import async_playwright
        except Exception as e:
            raise RuntimeError("Playwright not installed. Use: py -m pip install playwright") from e

        Path(self.profile_dir).mkdir(parents=True, exist_ok=True)
        queue: asyncio.Queue[DivergenceEvent] = asyncio.Queue()

        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=self.profile_dir,
                headless=False
            )
            page = await context.new_page()

            def on_console(msg):
                text = getattr(msg, "text", msg)
                ok, payload = _extract_payload(str(text))
                if not ok: return
                if isinstance(payload, dict):
                    ev = DivergenceEvent.from_raw(payload)
                    if ev:
                        asyncio.create_task(queue.put(ev))

            page.on("console", on_console)
            await page.goto(self.url)
            print("🟢 Listening… prefix:", PREFIX)

            try:
                while True:
                    ev = await queue.get()
                    yield ev
            finally:
                await context.close()
