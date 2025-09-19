# Scripts/Trading_Bot_Test3/CatchJS_Data_WS/PreprocessData/process_condition.py
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Iterable, Iterator, Optional

def _slim_event(ev: Dict[str, Any], *, mode: str = "strict") -> Dict[str, Any]:
    """
    Build a compact, deterministic view of an event for fingerprinting.
    - mode="strict": include prices + times (detect *any* change)
    - mode="times":  include only times (treat price-only nudges as same)
    """
    l1 = ev.get("L1") or ev.get("pivots", {}).get("L1", {}) or {}
    l2 = ev.get("L2") or ev.get("pivots", {}).get("L2", {}) or {}
    base = {
        "sequence": ev.get("sequence"),
        "side": ev.get("side"),
        "status": ev.get("status"),
        "tf_sec": ev.get("tf_sec"),
        "L1_time": l1.get("time"),
        "L2_time": l2.get("time"),
    }
    if mode == "strict":
        base.update({
            "L1_price": l1.get("price"),
            "L2_price": l2.get("price"),
        })
    return base

def fingerprint_block(block: List[Dict[str, Any]], *, mode: str = "strict") -> str:
    """
    Deterministic fingerprint for a whole block.
    `mode` controls sensitivity (see _slim_event).
    """
    slim = [_slim_event(ev, mode=mode) for ev in block]
    payload = json.dumps(slim, sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()

class BlockChangeFilter:
    """
    Remembers the last block fingerprint and tells you if a new block changed.
    Use one instance per stream.
    """
    def __init__(self, *, mode: str = "strict") -> None:
        self._last_fp: Optional[str] = None
        self._mode = mode

    def has_changed(self, block: List[Dict[str, Any]]) -> bool:
        fp = fingerprint_block(block, mode=self._mode)
        return fp != self._last_fp

    def remember(self, block: List[Dict[str, Any]]) -> None:
        self._last_fp = fingerprint_block(block, mode=self._mode)

    def filter(self, blocks: Iterable[List[Dict[str, Any]]]) -> Iterator[List[Dict[str, Any]]]:
        """Generator: yields only blocks that differ from the previous one."""
        for blk in blocks:
            if self.has_changed(blk):
                self.remember(blk)
                yield blk
