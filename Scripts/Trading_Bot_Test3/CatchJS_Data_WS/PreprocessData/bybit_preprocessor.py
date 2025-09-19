# Scripts/Trading_Bot_Test3/CatchJS_Data_WS/PreprocessData/bybit_preprocessor.py
from typing import List, Dict, Any
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.PreprocessData import sequence_store
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.PreprocessData import bybit_highs_lows_15m_batch as highs_lows

def process(data: Any, *, ticker: str = "BTC"):
    """
    If list[dict] -> compute Bybit 15m L1/L2 lows (−1h) + H1 highs and return list.
                     Persist each processed element exactly once.
    If dict -> pass through unchanged (no persistence).
    """
    if isinstance(data, list):
        try:
            processed_list: List[Dict[str, Any]] = highs_lows.process(data, ticker=ticker)
        except Exception as e:
            print(f"[bybit_preprocessor] ERROR fallback passthrough: {e}")
            processed_list = data  # fall back to raw if enrichment fails

        #for p in processed_list: sequence_store.save_data_locally(p)
        return processed_list

    # Single dict path: pass-through with no saving (avoids double writes).
    return dict(data)
