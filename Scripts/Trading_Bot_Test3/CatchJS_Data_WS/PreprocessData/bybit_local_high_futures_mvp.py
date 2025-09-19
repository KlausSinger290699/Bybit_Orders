# bybit_replace_lows_15m_batch.py
import ccxt
import json

DEFAULT_TYPE = "future"
QUOTE = "USDT"
CONTRACT_SUFFIX = ":USDT"
TF = "15m"

# aggr timestamps are ~1h ahead of Bybit(UTC) display → shift back 1 hour to match Bybit candles
AGGR_BYBIT_HOUR_SHIFT_MS = -3_600_000  # -1h

def symbol_for(ticker: str) -> str:
    return f"{ticker.strip().upper()}/{QUOTE}{CONTRACT_SUFFIX}"

def init_bybit_public() -> ccxt.bybit:
    ex = ccxt.bybit({"enableRateLimit": True})
    ex.options["defaultType"] = DEFAULT_TYPE
    ex.load_markets()
    return ex

def _step_ms(timeframe: str) -> int:
    return {"1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000, "1h": 3_600_000}[timeframe]

def _fetch_ohlcv_range(ex, symbol, timeframe, start_ms, end_ms, limit=1000):
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
    return out

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

# —— helper that makes the offset explicit ——
def aggr_bybit_minus_1h(ts_ms: int) -> int:
    """Apply the aggr→Bybit UTC offset of -1 hour to a millisecond timestamp."""
    return ts_ms + AGGR_BYBIT_HOUR_SHIFT_MS

def replace_lows_with_bybit_aggr_bybit_1h(seq_list: list[dict], *, ticker: str = "BTC") -> list[dict]:
    """
    Replace L1/L2 prices with Bybit 15m lows, applying aggr→Bybit UTC offset of -1h.
    """
    ex = init_bybit_public()
    symbol = symbol_for(ticker)
    step = _step_ms(TF)

    # Build a single fetch window covering all shifted L1/L2 times
    all_ts_shifted = []
    for s in seq_list:
        all_ts_shifted.append(aggr_bybit_minus_1h(int(s["L1"]["time"]) * 1000))
        all_ts_shifted.append(aggr_bybit_minus_1h(int(s["L2"]["time"]) * 1000))
    start_ms = _bucket_open(min(all_ts_shifted), step) - step  # small buffer
    end_ms   = _bucket_open(max(all_ts_shifted), step) + step

    candles = _fetch_ohlcv_range(ex, symbol, TF, start_ms, end_ms, limit=1000)

    # Update sequences in place with Bybit lows using shifted timestamps
    updated = []
    for s in seq_list:
        l1_ts_ms_shifted = aggr_bybit_minus_1h(int(s["L1"]["time"]) * 1000)
        l2_ts_ms_shifted = aggr_bybit_minus_1h(int(s["L2"]["time"]) * 1000)

        l1_old, l2_old = s["L1"]["price"], s["L2"]["price"]
        l1_low = _low_for_ts(candles, l1_ts_ms_shifted, step)
        l2_low = _low_for_ts(candles, l2_ts_ms_shifted, step)

        s2 = {**s}
        s2["L1"] = {**s["L1"], "price": l1_low}
        s2["L2"] = {**s["L2"], "price": l2_low}

        updated.append(s2)
        print(f"{s.get('status','')} {s.get('side','')} | "
              f"L1 {l1_old} → {l1_low}  |  L2 {l2_old} → {l2_low}")

    return updated

if __name__ == "__main__":
    seq_list = [
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

    updated = replace_lows_with_bybit_aggr_bybit_1h(seq_list, ticker="BTC")
    print(json.dumps(updated, ensure_ascii=False, indent=2))
