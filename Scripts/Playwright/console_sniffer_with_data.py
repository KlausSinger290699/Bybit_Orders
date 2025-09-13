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
    """Central store for all divergence threads."""
    def __init__(self):
        self._threads: Dict[str, Thread] = {}

    def add_event(self, data: dict):
        event = DivergenceEvent(data)
        tid = event.thread_id

        if tid not in self._threads:
            self._threads[tid] = Thread(thread_id=tid, side=event.side)

        self._threads[tid].add_event(event)
        print(f"📌 Stored event #{event.sequence} for {tid} ({event.side}, {event.status})")

    def get_thread(self, thread_id: str) -> Optional[Thread]:
        return self._threads.get(thread_id)

    def all_threads(self) -> List[Thread]:
        return list(self._threads.values())

    def to_dict(self) -> dict:
        return {tid: thread.to_dict() for tid, thread in self._threads.items()}

    def save_json(self, path: Path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
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

        def on_console(msg):
            text = getattr(msg, "text", msg)
            ok, payload = extract_payload(str(text))
            if ok and isinstance(payload, dict):
                store.add_event(payload)

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
