# Scripts/Trading_Bot_Test3/CatchJS_Data_WS/PreprocessData/bybit_preprocessor.py
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.PreprocessData import sequence_store
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.PreprocessData import bybit_highs_lows_15m_batch as highs_lows

def _process_one(payload: dict, *, ticker: str = "BTC") -> dict:
    # single dicts aren’t expected for the highs/lows module — just store passthrough
    processed = dict(payload)
    
    # TODO: Find a good place to save locally store data without github syncing it
    #sequence_store.save_data_locally(processed)
    return processed

def process(data, *, ticker: str = "BTC"):
    """
    If dict -> process one and return dict.
    If list[dict] -> compute Bybit 15m L1/L2 lows (−1h) + H1 highs and return list.
    """
    if isinstance(data, list):
        try:
            processed_list = highs_lows.process(data, ticker=ticker)  # prints console lines + returns enriched list
        except Exception as e:
            print(f"[bybit_preprocessor] ERROR fallback passthrough: {e}")
            processed_list = data
        for p in processed_list:
            sequence_store.save_data_locally(p)
        return processed_list

    return _process_one(data, ticker=ticker)