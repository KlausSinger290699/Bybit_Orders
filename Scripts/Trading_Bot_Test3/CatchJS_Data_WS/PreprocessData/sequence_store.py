import json
from pathlib import Path
from typing import Optional
from datetime import datetime

# Directories/files (computed at import/init)
BASE_DIR: Optional[Path] = None          # .../Scripts/Trading_Bot_Test3
DATA_DIR: Optional[Path] = None          # .../Scripts/Trading_Bot_Test3/data
SEQ_SAVE_DIR: Optional[Path] = None      # .../Scripts/Trading_Bot_Test3/data/sequences_YYYYMMDD_HHMMSS
LAST_PAYLOAD_PATH: Optional[Path] = None # .../data/last_payload.json
RUN_ID: Optional[str] = None             # YYYYMMDD_HHMMSS

# Sequence buffer state
_current_seq: Optional[int] = None
_seq_buf: list[dict] = []


def init_storage():
    """Create data/ and per-run data/sequences_YYYYMMDD_HHMMSS under Scripts/Trading_Bot_Test3."""
    global BASE_DIR, DATA_DIR, SEQ_SAVE_DIR, LAST_PAYLOAD_PATH, RUN_ID
    if BASE_DIR is not None:
        return  # already inited

    # this file is at .../Scripts/Trading_Bot_Test3/CatchJS_Data_WS/PreprocessData/sequence_store.py
    BASE_DIR = Path(__file__).resolve().parents[2]  # -> .../Trading_Bot_Test3
    DATA_DIR = BASE_DIR / "data"
    RUN_ID = datetime.now().strftime("%Y%m%d_%H%M%S")
    SEQ_SAVE_DIR = DATA_DIR / f"sequences_{RUN_ID}"
    LAST_PAYLOAD_PATH = DATA_DIR / "last_payload.json"

    DATA_DIR.mkdir(exist_ok=True)
    SEQ_SAVE_DIR.mkdir(exist_ok=True)


def save_event(event: dict):
    """Save latest single event AND buffer by sequence; dump when sequence changes."""
    global _current_seq, _seq_buf

    if LAST_PAYLOAD_PATH is None or SEQ_SAVE_DIR is None:
        init_storage()

    # 1) Always write latest payload (debug/inspection)
    LAST_PAYLOAD_PATH.write_text(json.dumps(event, indent=2))

    # 2) Buffer per-sequence and dump on change
    seq = event.get("sequence")
    if seq is None:
        return  # ignore if bad payload

    if _current_seq is None:
        _current_seq = seq

    if seq != _current_seq:
        _dump_current_sequence()
        _seq_buf = []
        _current_seq = seq

    _seq_buf.append(event)


def flush():
    """Dump any remaining buffered sequence to disk."""
    if _seq_buf:
        _dump_current_sequence()


def _dump_current_sequence():
    """Write the buffered events of the current sequence to a file."""
    if _current_seq is None or not _seq_buf or SEQ_SAVE_DIR is None:
        return
    out_path = SEQ_SAVE_DIR / f"seq_{_current_seq}.json"
    out_path.write_text(json.dumps(_seq_buf, indent=2))
