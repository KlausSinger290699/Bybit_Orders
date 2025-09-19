# Scripts/Trading_Bot_Test3/CatchJS_Data_WS/PreprocessData/sequence_order.py
from typing import List, Dict, Any

def _l1_time(ev: Dict[str, Any]) -> int:
    """
    Extract L1.time (seconds) from event. Falls back to pivots.L1.time.
    Returns a large value if missing so bad items sort last.
    """
    try:
        l1 = ev.get("L1") or ev.get("pivots", {}).get("L1", {})
        return int(l1.get("time"))  # seconds
    except Exception:
        return 10**15  # push malformed to end

def order_by_l1_time(block: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort a sequence block (list[dict]) by L1.time ascending.
    Stable sort: preserves original order for ties/missing.
    """
    if not isinstance(block, list):
        return block
    return sorted(block, key=_l1_time)
