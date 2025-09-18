from dataclasses import dataclass
from typing import Dict, Optional
from . import utils

@dataclass(frozen=True)
class EngineConfig:
    max_pivot_time_diff_sec: int = 0

class StrategyEngine:
    def __init__(self, cfg: EngineConfig = EngineConfig()):
        self.cfg = cfg
        self._l2_index: Dict[int, dict] = {}
        self._printed: set[str] = set()

    @staticmethod
    def _safe_int(x) -> Optional[int]:
        try:
            return int(x)
        except Exception:
            return None

    def _store_prior_bull_l2(self, ev: dict):
        if ev.get("side") != "bull":
            return
        if ev.get("status") not in ("✅", "❔"):
            return
        _l1, l2 = utils.extract_L1_L2(ev)
        t = self._safe_int(l2.get("time"))
        if t is not None:
            self._l2_index[t] = ev

    def _match_prev_l2_with_curr_l1(self, curr: dict):
        if curr.get("side") != "bull" or curr.get("status") != "❔":
            return None
        l1, _ = utils.extract_L1_L2(curr)
        return self._l2_index.get(self._safe_int(l1.get("time")))

    def on_event(self, ev: dict):
        prev = self._match_prev_l2_with_curr_l1(ev)
        if prev:
            entry_key = f"{prev.get('thread_id')}->{ev.get('thread_id')}"
            if entry_key not in self._printed:
                self._printed.add(entry_key)
                self._print_entry(prev, ev)
        self._store_prior_bull_l2(ev)

    def _print_entry(self, prev: dict, curr: dict):
        curr_l1, _ = utils.extract_L1_L2(curr)
        _prev_l1, prev_l2 = utils.extract_L1_L2(prev)
        print("\n🟢📣 ENTRY SIGNAL (Bull)")
        print(f"   ├─ Prev Thread: {prev.get('thread_id')}")
        print(f"   ├─ Curr Thread: {curr.get('thread_id')}")
        print(f"   ├─ L2(prev) == L1(curr): time={prev_l2.get('time')}  price={utils.fmt_price(prev_l2.get('price'))}")
