# core.py
import asyncio
from dataclasses import dataclass
from typing import Optional, Dict
from abc import ABC, abstractmethod

# =========================
# Domain: Events & Helpers
# =========================

@dataclass(frozen=True)
class DivergenceEvent:
    v: int
    source: str
    tf_sec: Optional[int]
    side: str           # "bull" | "bear"
    status: str         # "✅" | "❔" | "❌"
    thread_id: str
    sequence: int
    L1_time: Optional[int] = None
    L1_price: Optional[float] = None
    L2_time: Optional[int] = None
    L2_price: Optional[float] = None

    @classmethod
    def from_raw(cls, raw: dict) -> Optional["DivergenceEvent"]:
        if not isinstance(raw, dict): return None
        if raw.get("v") != 1: return None
        if raw.get("source") != "aggr/indicator": return None
        if not isinstance(raw.get("thread_id"), str): return None
        if not isinstance(raw.get("sequence"), int): return None
        if not isinstance(raw.get("side"), str): return None
        if not isinstance(raw.get("status"), str): return None

        piv = raw.get("pivots") or {}
        L1 = raw.get("L1") or piv.get("L1") or {}
        L2 = raw.get("L2") or piv.get("L2") or {}

        def as_int(x):
            try: return int(x)
            except: return None
        def as_float(x):
            try: return float(x)
            except: return None

        return cls(
            v=1,
            source="aggr/indicator",
            tf_sec=as_int(raw.get("tf_sec")),
            side=raw["side"],
            status=raw["status"],
            thread_id=raw["thread_id"],
            sequence=raw["sequence"],
            L1_time=as_int(L1.get("time")),
            L1_price=as_float(L1.get("price")),
            L2_time=as_int(L2.get("time")),
            L2_price=as_float(L2.get("price")),
        )

def fmt_tf(sec: Optional[int]) -> str:
    table = {
        60:"1m", 120:"2m", 180:"3m", 300:"5m", 600:"10m", 900:"15m",
        1200:"20m", 1800:"30m", 3600:"1h", 7200:"2h", 14400:"4h",
        21600:"6h", 43200:"12h", 86400:"1d"
    }
    if sec is None: return "?"
    return table.get(sec, f"{sec}s")

def pstr(x) -> str:
    if isinstance(x, (int, float)):
        return f"{int(round(x))}"
    return "?"

# =========================
# Ports (Interfaces)
# =========================

class EventSink(ABC):
    @abstractmethod
    def on_event(self, ev: DivergenceEvent) -> None: ...
    @abstractmethod
    def on_entry_signal(self, prev: DivergenceEvent, curr: DivergenceEvent) -> None: ...

class EventSource(ABC):
    @abstractmethod
    async def events(self):  # AsyncIterator[DivergenceEvent]
        ...

# =========================
# Strategy (Use Case)
# =========================

@dataclass(frozen=True)
class EngineConfig:
    # For now: exact L2(prev) == L1(curr); extend later for time-window tolerance
    max_pivot_time_diff_sec: int = 0

class StrategyEngine:
    """
    Rule:
      Previous bull (✅ or ❔) with L2
      AND next bull (❔) whose L1 == previous L2
      → print: enter 1% risk, SL on L1 (= prev L2)
    """
    def __init__(self, sink: EventSink, cfg: EngineConfig = EngineConfig()):
        self.cfg = cfg
        self._sink = sink
        self._l2_by_time: Dict[int, DivergenceEvent] = {}
        self._printed: set[str] = set()

    def on_event(self, ev: DivergenceEvent):
        prev = self._match_prev_l2_with_curr_l1(ev)
        if prev:
            key = f"{prev.thread_id}->{ev.thread_id}"
            if key not in self._printed:
                self._printed.add(key)
                self._sink.on_entry_signal(prev, ev)

        self._index_if_candidate(ev)
        self._sink.on_event(ev)  # always forward

    def _index_if_candidate(self, ev: DivergenceEvent):
        if ev.side != "bull": return
        if ev.status not in ("✅", "❔"): return
        if ev.L2_time is None: return
        self._l2_by_time[ev.L2_time] = ev

    def _match_prev_l2_with_curr_l1(self, curr: DivergenceEvent) -> Optional[DivergenceEvent]:
        if curr.side != "bull": return None
        if curr.status != "❔": return None
        if curr.L1_time is None: return None
        # Exact match for now; later: search within ±cfg.max_pivot_time_diff_sec
        return self._l2_by_time.get(curr.L1_time)
