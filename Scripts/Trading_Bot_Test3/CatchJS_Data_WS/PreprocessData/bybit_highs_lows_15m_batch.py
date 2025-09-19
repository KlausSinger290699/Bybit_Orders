# bybit_highs_lows_15m_batch.py
# Replace L1/L2 with Bybit 15m lows (−1h aggr→Bybit) and insert H1 high after L2.
# Reuses fully-enriched results when thread_id or pair_id matches a prior entry.
# Includes lightweight cache metrics + optional debug logs.

from __future__ import annotations

import json
import time
from threading import Thread, Event, Lock
from typing import Any, Dict, List, Tuple, Optional

import ccxt

# -------------------- config --------------------
DEFAULT_TYPE = "future"
QUOTE = "USDT"
CONTRACT_SUFFIX = ":USDT"
TF = "15m"
AGGR_BYBIT_HOUR_SHIFT_MS = -3_600_000  # -1h

# -------------------- debug & metrics --------------------
DEBUG = False
_METRICS = {
    "cache_puts": 0,
    "cache_hit_thread": 0,
    "cache_hit_pair": 0,
    "reused_items": 0,
    "computed_items": 0,
    "fetch_calls": 0,  # how many OHLCV-range fetches we performed
}

def enable_cache_debug(flag: bool = True):
    """Turn on/off verbose cache/reuse logs."""
    global DEBUG
    DEBUG = bool(flag)

def cache_stats() -> dict:
    """Return a shallow copy of current metrics."""
    return dict(_METRICS)

def reset_cache_stats():
    """Reset metrics counters."""
    for k in _METRICS:
        _METRICS[k] = 0

# -------------------- spinner helpers --------------------
def _spinner(label: str, stop: Event, interval: float = 0.1):
    glyphs = "|/-\\"
    i = 0
    while not stop.is_set():
        print(f"\r{label} {glyphs[i % len(glyphs)]}", end="", flush=True)
        i += 1
        time.sleep(interval)

def _clear_line():
    print("\r" + " " * 120 + "\r", end="", flush=True)

def with_spinner(label: str, fn, *args, done_message: str | None = None, **kwargs):
    stop = Event()
    t = Thread(target=_spinner, args=(label, stop), daemon=True)
    t.start()
    try:
        return fn(*args, **kwargs)
    finally:
        stop.set()
        t.join()
        if done_message is not None:
            # wipe spinner line, then print the final message on a fresh line
            print("\r" + " " * 120, end="\r", flush=True)
            print(done_message, flush=True)
        else:
            _clear_line()

# -------------------- singleton ccxt.bybit --------------------
_EX_LOCK = Lock()
_EX_SINGLETON: ccxt.bybit | None = None
_MARKETS_LOADED = False

def symbol_for(ticker: str) -> str:
    if not isinstance(ticker, str):
        raise TypeError(f"ticker must be str, got {type(ticker).__name__}")
    return f"{ticker.strip().upper()}/{QUOTE}{CONTRACT_SUFFIX}"

def init_bybit_public() -> ccxt.bybit:
    """Thread-safe singleton; loads markets once (with spinner + done message)."""
    global _EX_SINGLETON, _MARKETS_LOADED
    with _EX_LOCK:
        if _EX_SINGLETON is None:
            ex = ccxt.bybit({"enableRateLimit": True})
            ex.options["defaultType"] = DEFAULT_TYPE
            print("Loading markets (Bybit | public)…")
            with_spinner("Loading markets", ex.load_markets, done_message="Loading markets done. ✅")
            _EX_SINGLETON = ex
            _MARKETS_LOADED = True
        elif not _MARKETS_LOADED:
            print("Loading markets (Bybit | public)…")
            with_spinner("Loading markets", _EX_SINGLETON.load_markets, done_message="Loading markets done. ✅")
            _MARKETS_LOADED = True
        return _EX_SINGLETON

# -------------------- candle utils --------------------
def _step_ms(timeframe: str) -> int:
    return {"1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000}[timeframe]

def _fetch_ohlcv_range(ex, symbol, timeframe, start_ms, end_ms, limit=1000, *, progress: bool = False):
    """
    Fetch candles for [start_ms, end_ms].
    - If progress=True, show a spinner labeled "Fetching {timeframe} OHLCV for {symbol}" while running,
      and clear the line on completion (NO '... done.' message).
    - If progress=False, run silently.
    """
    _METRICS["fetch_calls"] += 1  # count per consolidated fetch
    label = f"Fetching {timeframe} OHLCV for {symbol}"

    def _do_fetch():
        out, since = [], start_ms
        step = _step_ms(timeframe)
        while since <= end_ms:
            batch = ex.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)
            if not batch:
                break
            for c in batch:
                if c[0] > end_ms:
                    break
                if c[0] >= start_ms:
                    out.append(c)  # [ts, o, h, l, c, v]
            nxt = batch[-1][0] + step
            if nxt <= since:
                break
            since = nxt
            if len(batch) < limit:
                break
            time.sleep(0.01)  # tiny pause; ccxt also rate-limits
        return out

    if progress:
        return with_spinner(label, _do_fetch, done_message=None)
    else:
        return _do_fetch()

def _bucket_open(ts_ms: int, step_ms: int) -> int:
    return (ts_ms // step_ms) * step_ms

def _low_for_ts(candles: list[list], ts_ms: int, step_ms: int) -> float:
    bo = _bucket_open(ts_ms, step_ms)
    for o, _o, _h, l, _c, _v in candles:
        if o == bo:
            return float(l)
    for o, _o, _h, l, _c, _v in candles:
        if o <= ts_ms < o + step_ms:
            return float(l)
    raise RuntimeError(f"{TF} candle not found for ts={ts_ms}")

def _h1_high_between(candles: list[list], start_ms: int, end_ms: int) -> tuple[float, int]:
    w = [c for c in candles if start_ms <= c[0] <= end_ms]
    if not w:
        raise RuntimeError("No candles in L1→L2 window")
    hi = max(w, key=lambda r: r[2])
    return float(hi[2]), int(hi[0])

def aggr_bybit_minus_1h(ts_ms: int) -> int:
    return ts_ms + AGGR_BYBIT_HOUR_SHIFT_MS

def _with_h1_after_l2(s: dict, *, l1_low: float, l2_low: float, h1_price: float, h1_ts_ms: int) -> dict:
    """Return a new dict where H1 appears immediately after L2 (readability)."""
    out: Dict[str, Any] = {}
    for k in s.keys():
        if k == "L1":
            out["L1"] = {**s["L1"], "price": l1_low}
        elif k == "L2":
            out["L2"] = {**s["L2"], "price": l2_low}
            out["H1"] = {"time": h1_ts_ms // 1000, "price": h1_price}
        elif k == "H1":
            continue
        else:
            out[k] = s[k]
    if "L1" not in out:
        out["L1"] = {**s.get("L1", {}), "price": l1_low}
    if "L2" not in out:
        out["L2"] = {**s.get("L2", {}), "price": l2_low}
        out["H1"] = {"time": h1_ts_ms // 1000, "price": h1_price}
    return out

# -------------------- Reuse/Caching Layer (exact-id reuse only) --------------
class PivotCache:
    """Minimal cache for previously computed pivots keyed by thread_id/pair_id."""
    def __init__(self):
        self._by_thread: Dict[str, Dict[str, Any]] = {}
        self._by_pair: Dict[str, Dict[str, Any]] = {}

    def put(self, item: Dict[str, Any]) -> None:
        tid = item.get("thread_id")
        pid = item.get("pair_id")
        if tid:
            self._by_thread[tid] = item
        if pid:
            self._by_pair[pid] = item
        _METRICS["cache_puts"] += 1
        if DEBUG:
            print(f"[cache] put tid={tid} pid={pid}")

    def get_by_thread(self, thread_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not thread_id:
            return None
        hit = self._by_thread.get(thread_id)
        if hit is not None:
            _METRICS["cache_hit_thread"] += 1
            if DEBUG:
                print(f"[cache] HIT(thread) {thread_id}")
        return hit

    def get_by_pair(self, pair_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not pair_id:
            return None
        hit = self._by_pair.get(pair_id)
        if hit is not None:
            _METRICS["cache_hit_pair"] += 1
            if DEBUG:
                print(f"[cache] HIT(pair) {pair_id}")
        return hit

_CACHE = PivotCache()

def _is_enriched(x: Dict[str, Any]) -> bool:
    try:
        return (
            isinstance(x["L1"]["price"], (int, float)) and
            isinstance(x["L2"]["price"], (int, float)) and
            isinstance(x["H1"]["price"], (int, float)) and
            isinstance(x["H1"]["time"], (int, float))
        )
    except Exception:
        return False

def plan_reuse(items: List[Dict[str, Any]], cache: PivotCache
               ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Decide which items can be reused vs. need compute.
    Returns (to_compute, reused_ready)

    Rules:
      - If (thread_id) OR (pair_id) found in cache with enriched L1/L2/H1, reuse entirely.
      - No special handling for '❔' — anything else recomputes fully.
    """
    to_compute: List[Dict[str, Any]] = []
    reused: List[Dict[str, Any]] = []

    for s in items:
        prev = cache.get_by_thread(s.get("thread_id")) or cache.get_by_pair(s.get("pair_id"))
        if prev and _is_enriched(prev):
            reused.append({
                **s,
                "L1": {**s.get("L1", {}), "price": prev["L1"]["price"]},
                "L2": {**s.get("L2", {}), "price": prev["L2"]["price"]},
                "H1": {"time": prev["H1"]["time"], "price": prev["H1"]["price"]},
            })
            _METRICS["reused_items"] += 1
            if DEBUG:
                print(f"[reuse] {s.get('thread_id')} | {s.get('pair_id')}")
        else:
            to_compute.append(s)

    return to_compute, reused

# -------------------- public API --------------------
def process(rawdata: List[Dict[str, Any]], *, ticker: str = "BTC", progress: bool = False,
            cache: PivotCache = _CACHE) -> List[Dict[str, Any]]:
    """
    Replace L1/L2 with Bybit 15m lows (−1h aggr→Bybit) and insert H1 high after L2.
    Reuse only when exact thread_id or pair_id matches a previously enriched entry.
    Set progress=True to show a fetching spinner (no 'done' message).
    """
    if not rawdata:
        return []

    # 1) reuse decision
    to_compute, reused_ready = plan_reuse(rawdata, cache)

    # 2) if nothing to compute, return reused
    if not to_compute:
        return reused_ready

    # 3) compute candles only for what's left
    ex = init_bybit_public()
    symbol = symbol_for(ticker)
    step = _step_ms(TF)

    # unified fetch window across all shifted L1/L2 (compute-only set)
    all_ts: List[int] = []
    for s in to_compute:
        if "L1" in s and "L2" in s:
            all_ts.append(aggr_bybit_minus_1h(int(s["L1"]["time"]) * 1000))
            all_ts.append(aggr_bybit_minus_1h(int(s["L2"]["time"]) * 1000))

    if not all_ts:
        # nothing needs data; return what we have
        for r in reused_ready:
            if _is_enriched(r):
                cache.put(r)
        return reused_ready

    start_ms = _bucket_open(min(all_ts), step) - step
    end_ms   = _bucket_open(max(all_ts), step) + step
    candles = _fetch_ohlcv_range(ex, symbol, TF, start_ms, end_ms, limit=1000, progress=progress)

    computed: List[Dict[str, Any]] = []
    for s in to_compute:
        l1_ts = aggr_bybit_minus_1h(int(s["L1"]["time"]) * 1000)
        l2_ts = aggr_bybit_minus_1h(int(s["L2"]["time"]) * 1000)

        l1_low = _low_for_ts(candles, l1_ts, step)
        l2_low = _low_for_ts(candles, l2_ts, step)
        t_start, t_end = (l1_ts, l2_ts) if l1_ts <= l2_ts else (l2_ts, l1_ts)
        h1_price, h1_ts = _h1_high_between(candles, t_start, t_end)

        s2 = _with_h1_after_l2(s, l1_low=l1_low, l2_low=l2_low, h1_price=h1_price, h1_ts_ms=h1_ts)
        computed.append(s2)
        cache.put(s2)  # update cache with fully enriched entry

    _METRICS["computed_items"] += len(computed)

    # 4) merge in original order (computed overrides reused when both exist)
    def _fid(x: Dict[str, Any]) -> Tuple[str, str]:
        return (x.get("thread_id", ""), x.get("pair_id", ""))

    comp_idx = { _fid(x): x for x in computed }
    out: List[Dict[str, Any]] = []
    for s in rawdata:
        key = _fid(s)
        if key in comp_idx:
            out.append(comp_idx[key])
        else:
            rr = next((r for r in reused_ready if _fid(r) == key), s)
            out.append(rr)
            if _is_enriched(rr):
                cache.put(rr)

    return out

# -------------------- standalone sample --------------------
SEQ_1 = [
  {
    "v": 1, "source": "aggr/indicator", "tf_sec": 900, "side": "bull", "status": "✅",
    "thread_id": "bull:113420.64-114398.93:900", "pair_id": "L1:113420.64|L2:114398.93", "sequence": 1,
    "L1": {"time": 1757597400, "price": 113242.0},
    "L2": {"time": 1757952900, "price": 114340.0},
    "H1": {"time": 1757916000, "price": 116761.3},
    "cvd": {"L1": -910772639, "L2": -931816191},
    "meta": {"start": 1757952900, "end": 1757597400, "sIndex": 384, "eIndex": 779}
  },
  {
    "v": 1, "source": "aggr/indicator", "tf_sec": 900, "side": "bull", "status": "✅",
    "thread_id": "bull:114385.49-114710.52:900", "pair_id": "L1:114385.49|L2:114710.52", "sequence": 1,
    "L1": {"time": 1757946600, "price": 114316.3},
    "L2": {"time": 1758138300, "price": 114710.0},
    "H1": {"time": 1758093300, "price": 117239.5},
    "cvd": {"L1": -943267646, "L2": -957691958},
    "meta": {"start": 1758138300, "end": 1757946600, "sIndex": 178, "eIndex": 391}
  },
  {
    "v": 1, "source": "aggr/indicator", "tf_sec": 900, "side": "bull", "status": "❔",
    "thread_id": "bull:114710.52-115466.41:900", "pair_id": "L1:114710.52|L2:115466.41", "sequence": 1,
    "L1": {"time": 1758138300, "price": 114710.0},
    "L2": {"time": 1758297600, "price": 115408.0},
    "H1": {"time": 1758219300, "price": 117884.0},
    "cvd": {"L1": -19924566680.51148, "L2": -21455611296.996433},
    "meta": {"start": 1758297600, "end": 1758138300, "sIndex": 1, "eIndex": 178}
  }
]

SEQ_2 = [
  {
    "v": 1, "source": "aggr/indicator", "tf_sec": 900, "side": "bull", "status": "✅",
    "thread_id": "bull:113420.64-114398.93:900", "pair_id": "L1:113420.64|L2:114398.93", "sequence": 2,
    "L1": {"time": 1757597400, "price": 113242.0},
    "L2": {"time": 1757952900, "price": 114340.0},
    "H1": {"time": 1757916000, "price": 116761.3},
    "cvd": {"L1": -910772639, "L2": -931816191},
    "meta": {"start": 1757952900, "end": 1757597400, "sIndex": 384, "eIndex": 779}
  },
  {
    "v": 1, "source": "aggr/indicator", "tf_sec": 900, "side": "bull", "status": "✅",
    "thread_id": "bull:114385.49-114710.52:900", "pair_id": "L1:114385.49|L2:114710.52", "sequence": 2,
    "L1": {"time": 1757946600, "price": 114316.3},
    "L2": {"time": 1758138300, "price": 114710.0},
    "H1": {"time": 1758093300, "price": 117239.5},
    "cvd": {"L1": -943267646, "L2": -957691958},
    "meta": {"start": 1758138300, "end": 1757946600, "sIndex": 178, "eIndex": 391}
  },
  {
    "v": 1, "source": "aggr/indicator", "tf_sec": 900, "side": "bull", "status": "❔",
    "thread_id": "bull:114710.52-115466.41:900", "pair_id": "L1:114710.52|L2:115466.41", "sequence": 2,
    "L1": {"time": 1758138300, "price": 114710.0},
    "L2": {"time": 1758297600, "price": 115408.0},
    "H1": {"time": 1758219300, "price": 117884.0},
    "cvd": {"L1": -19924566680.51148, "L2": -21455611296.996433},
    "meta": {"start": 1758297600, "end": 1758138300, "sIndex": 1, "eIndex": 178}
  }
]

SEQ_3 = [
  {
    "v": 1, "source": "aggr/indicator", "tf_sec": 900, "side": "bull", "status": "✅",
    "thread_id": "bull:113420.64-114398.93:900", "pair_id": "L1:113420.64|L2:114398.93", "sequence": 3,
    "L1": {"time": 1757597400, "price": 113242.0},
    "L2": {"time": 1757952900, "price": 114340.0},
    "H1": {"time": 1757916000, "price": 116761.3},
    "cvd": {"L1": -910772639, "L2": -931816191},
    "meta": {"start": 1757952900, "end": 1757597400, "sIndex": 384, "eIndex": 779}
  },
  {
    "v": 1, "source": "aggr/indicator", "tf_sec": 900, "side": "bull", "status": "✅",
    "thread_id": "bull:114385.49-114710.52:900", "pair_id": "L1:114385.49|L2:114710.52", "sequence": 3,
    "L1": {"time": 1757946600, "price": 114316.3},
    "L2": {"time": 1758138300, "price": 114710.0},
    "H1": {"time": 1758093300, "price": 117239.5},
    "cvd": {"L1": -943267646, "L2": -957691958},
    "meta": {"start": 1758138300, "end": 1757946600, "sIndex": 178, "eIndex": 391}
  },
  {
    "v": 1, "source": "aggr/indicator", "tf_sec": 900, "side": "bull", "status": "❔",
    "thread_id": "bull:114710.52-115466.41:900", "pair_id": "L1:114710.52|L2:115466.41", "sequence": 3,
    "L1": {"time": 1758138300, "price": 114710.0},
    "L2": {"time": 1758297600, "price": 115408.0},
    "H1": {"time": 1758219300, "price": 117884.0},
    "cvd": {"L1": -19924566680.51148, "L2": -21455611296.996433},
    "meta": {"start": 1758297600, "end": 1758138300, "sIndex": 1, "eIndex": 178}
  }
]

def _print_preview(sample_seq_list, updated):
    for orig, new in zip(sample_seq_list, updated):
        l1_old = orig["L1"]["price"]
        l2_old = orig["L2"]["price"]
        l1_new = new["L1"]["price"]
        l2_new = new["L2"]["price"]
        h1_p   = new["H1"]["price"]
        h1_ts  = new["H1"]["time"] * 1000  # ms for logs
        print(f"{new.get('status','')} {new.get('side','')} | "
              f"L1 {l1_old} → {l1_new} | L2 {l2_old} → {l2_new} | "
              f"H1 {h1_p} @ {h1_ts}")

if __name__ == "__main__":
    enable_cache_debug(False)

    # Warm-up markets so logs are tidy
    init_bybit_public()
    reset_cache_stats()

    print("\n=== Run A: SEQ_1 (compute expected) ===")
    out1 = process(SEQ_1, ticker="BTC", progress=True)
    _print_preview(SEQ_1, out1)
    print("Stats after Run A:", cache_stats())

    print("\n=== Run B: SEQ_2 (reuse expected by thread_id/pair_id) ===")
    out2 = process(SEQ_2, ticker="BTC", progress=False)
    _print_preview(SEQ_2, out2)
    print("Stats after Run B:", cache_stats())

    print("\n=== Run C: SEQ_3 (reuse expected again) ===")
    out3 = process(SEQ_3, ticker="BTC", progress=False)
    _print_preview(SEQ_3, out3)
    print("Stats after Run C:", cache_stats())

    print("\nExpectations:")
    print(f"- Run A: computed_items increases by {len(SEQ_1)}, fetch_calls = 1")
    print("- Run B & C: reused_items increases by ~len(batch) each, fetch_calls should not increase")
