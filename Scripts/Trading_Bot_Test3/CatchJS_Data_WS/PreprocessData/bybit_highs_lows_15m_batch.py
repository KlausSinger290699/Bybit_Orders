# bybit_highs_lows_15m_batch.py
import ccxt
import json
import time
from threading import Thread, Event, Lock

# -------------------- config --------------------
DEFAULT_TYPE = "future"
QUOTE = "USDT"
CONTRACT_SUFFIX = ":USDT"
TF = "15m"
AGGR_BYBIT_HOUR_SHIFT_MS = -3_600_000  # -1h

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
            with_spinner("Loading markets", ex.load_markets, done_message="Loading markets done. ✅\n")
            _EX_SINGLETON = ex
            _MARKETS_LOADED = True
        elif not _MARKETS_LOADED:
            print("Loading markets (Bybit | public)…")
            with_spinner("Loading markets", _EX_SINGLETON.load_markets, done_message="Loading markets done. ✅")
            _MARKETS_LOADED = True
            print("Ready.\n")
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
    label = f"Fetching {timeframe} OHLCV for {symbol}"  # printed only while spinner is active

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
            # tiny pause to be nice to API; ccxt also rate-limits
            time.sleep(0.01)
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
    raise RuntimeError(f"15m candle not found for ts={ts_ms}")

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
    out = {}
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

# -------------------- public API --------------------
def process(rawdata: list[dict], *, ticker: str = "BTC", progress: bool = False) -> list[dict]:
    """
    Replace L1/L2 with Bybit 15m lows (−1h aggr→Bybit) and insert H1 high after L2.
    Set progress=True to show a fetching spinner (no 'done' message).
    """
    ex = init_bybit_public()
    symbol = symbol_for(ticker)
    step = _step_ms(TF)

    # unified fetch window across all shifted L1/L2
    all_ts = []
    for s in rawdata:
        all_ts.append(aggr_bybit_minus_1h(int(s["L1"]["time"]) * 1000))
        all_ts.append(aggr_bybit_minus_1h(int(s["L2"]["time"]) * 1000))
    start_ms = _bucket_open(min(all_ts), step) - step
    end_ms   = _bucket_open(max(all_ts), step) + step
    candles = _fetch_ohlcv_range(ex, symbol, TF, start_ms, end_ms, limit=1000, progress=progress)

    updated = []
    for s in rawdata:
        l1_ts = aggr_bybit_minus_1h(int(s["L1"]["time"]) * 1000)
        l2_ts = aggr_bybit_minus_1h(int(s["L2"]["time"]) * 1000)

        l1_low = _low_for_ts(candles, l1_ts, step)
        l2_low = _low_for_ts(candles, l2_ts, step)
        t_start, t_end = (l1_ts, l2_ts) if l1_ts <= l2_ts else (l2_ts, l1_ts)
        h1_price, h1_ts = _h1_high_between(candles, t_start, t_end)

        s2 = _with_h1_after_l2(s, l1_low=l1_low, l2_low=l2_low, h1_price=h1_price, h1_ts_ms=h1_ts)
        updated.append(s2)

    return updated

# -------------------- standalone sample --------------------
SAMPLE_SEQ_LIST = [
  {
    "v": 1, "source": "aggr/indicator", "tf_sec": 900, "side": "bull", "status": "❔",
    "thread_id": "bull:1758138300-1758240000:900", "pair_id": "L1:1758138300|L2:1758240000", "sequence": 1,
    "L1": {"time": 1758138300, "price": 114710.5181818182},
    "L2": {"time": 1758240000, "price": 116631.62727272726},
    "cvd": {"L1": 597589528.6265794, "L2": -278522994.0802517},
    "meta": {"start": 1758240000, "end": 1758138300, "sIndex": 1, "eIndex": 114}
  },
  {
    "v": 1, "source": "aggr/indicator", "tf_sec": 900, "side": "bull", "status": "✅",
    "thread_id": "bull:1757946600-1758138300:900", "pair_id": "L1:1757946600|L2:1758138300", "sequence": 1,
    "L1": {"time": 1757946600, "price": 114385.49090909092},
    "L2": {"time": 1758138300, "price": 114710.5181818182},
    "cvd": {"L1": -110010445, "L2": -124434757},
    "meta": {"start": 1758138300, "end": 1757946600, "sIndex": 114, "eIndex": 327}
  },
  {
    "v": 1, "source": "aggr/indicator", "tf_sec": 900, "side": "bull", "status": "✅",
    "thread_id": "bull:1757597400-1757952900:900", "pair_id": "L1:1757597400|L2:1757952900", "sequence": 1,
    "L1": {"time": 1757597400, "price": 113420.63636363637},
    "L2": {"time": 1757952900, "price": 114398.92727272726},
    "cvd": {"L1": -77515438, "L2": -98558990},
    "meta": {"start": 1757952900, "end": 1757597400, "sIndex": 320, "eIndex": 715}
  },
  {
    "v": 1, "source": "aggr/indicator", "tf_sec": 900, "side": "bull", "status": "✅",
    "thread_id": "bull:1757554200-1757587500:900", "pair_id": "L1:1757554200|L2:1757587500", "sequence": 1,
    "L1": {"time": 1757554200, "price": 113657.63636363637},
    "L2": {"time": 1757587500, "price": 113778.15454545454},
    "cvd": {"L1": -293465982.92287177, "L2": -581573096.8806956},
    "meta": {"start": 1757587500, "end": 1757554200, "sIndex": 726, "eIndex": 763}
  }
]

def print_new_lows_and_highs(sample_seq_list, updated):
    # Pretty console preview (sample-only): show original → updated + H1
    for orig, new in zip(sample_seq_list, updated):
        l1_old = orig["L1"]["price"]
        l2_old = orig["L2"]["price"]
        l1_new = new["L1"]["price"]
        l2_new = new["L2"]["price"]
        h1_p   = new["H1"]["price"]
        h1_ts  = new["H1"]["time"] * 1000  # ms for consistency with logs
        print(f"{new.get('status','')} {new.get('side','')} | "
              f"L1 {l1_old} → {l1_new} | L2 {l2_old} → {l2_new} | "
              f"H1 {h1_p} @ {h1_ts}")

if __name__ == "__main__":
    # Standalone example: show a fetching spinner with no trailing "... done."
    updated = process(SAMPLE_SEQ_LIST, ticker="BTC", progress=True)
    print_new_lows_and_highs(SAMPLE_SEQ_LIST, updated)
    print("\n" + json.dumps(updated, ensure_ascii=False, indent=2))
