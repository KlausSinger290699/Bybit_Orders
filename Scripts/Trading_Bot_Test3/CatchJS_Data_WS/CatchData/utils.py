import json

# Inner width between the corners for the sequence bar
SEQ_TARGET_INNER = 58


def extract_payload(console_text: str, prefix: str):
    """Extract JSON payload after the given prefix."""
    if prefix not in console_text:
        return False, None
    after = console_text.split(prefix, 1)[1].strip()
    if after.startswith("{") or after.startswith("["):
        try:
            return True, json.loads(after)
        except json.JSONDecodeError:
            return True, after
    return True, after


def is_divergence_event(payload: dict) -> bool:
    """
    Accept only normalized 'aggr/indicator' events with basic shape and
    present L1/L2 (either top-level or within 'pivots').
    """
    if not isinstance(payload, dict):
        return False
    if payload.get("v") != 1:
        return False
    if payload.get("source") != "aggr/indicator":
        return False
    if not isinstance(payload.get("thread_id"), str):
        return False
    if not isinstance(payload.get("sequence"), int):
        return False
    if not isinstance(payload.get("side"), str):
        return False
    if not isinstance(payload.get("status"), str):
        return False

    l1, l2 = extract_L1_L2(payload)
    return isinstance(l1, dict) and isinstance(l2, dict)


def fmt_tf(sec) -> str:
    table = {
        60: "1m", 120: "2m", 180: "3m", 300: "5m", 600: "10m", 900: "15m",
        1200: "20m", 1800: "30m", 3600: "1h", 7200: "2h", 14400: "4h",
        21600: "6h", 43200: "12h", 86400: "1d"
    }
    try:
        sec = int(sec)
        return table.get(sec, f"{sec}s")
    except Exception:
        return "?"


def fmt_price(p):
    if isinstance(p, (int, float)):
        return f"{int(round(p))}"
    try:
        return f"{int(round(float(p)))}"
    except Exception:
        return "?"


def extract_L1_L2(data: dict):
    """
    Get L1/L2 dicts from either top-level fields or data['pivots'].
    """
    if isinstance(data.get("L1"), dict) or isinstance(data.get("L2"), dict):
        return data.get("L1") or {}, data.get("L2") or {}
    piv = data.get("pivots") or {}
    return piv.get("L1") or {}, piv.get("L2") or {}


def to_bold_unicode(s: str) -> str:
    """Bold letters and digits with math bold unicode (for pretty headers)."""
    out = []
    for ch in s:
        o = ord(ch)
        if 0x41 <= o <= 0x5A:      # A-Z
            out.append(chr(0x1D400 + (o - 0x41)))
        elif 0x61 <= o <= 0x7A:    # a-z
            out.append(chr(0x1D41A + (o - 0x61)))
        elif 0x30 <= o <= 0x39:    # 0-9
            out.append(chr(0x1D7CE + (o - 0x30)))
        else:
            out.append(ch)
    return "".join(out)


def _choose_tf_label(batch: list[dict]) -> str:
    """
    Pick tf label from the last event in batch that has tf_label or tf_sec.
    This avoids '?' on the first sequence.
    """
    for ev in reversed(batch):
        lbl = ev.get("tf_label")
        if lbl:
            return lbl
        sec = ev.get("tf_sec")
        if sec:
            return fmt_tf(sec)
    return "?"


def seq_bars(seq_no: int, tf_label: str):
    title = f"📌 {to_bold_unicode('Sequence')} \uFF03{to_bold_unicode(str(seq_no))} — {to_bold_unicode(tf_label)} "
    left_prefix = "━━ "
    inner_base = left_prefix + title
    fill_len = max(0, SEQ_TARGET_INNER - len(inner_base))
    inner_line = inner_base + ("━" * fill_len)
    top = f"┏{inner_line}┓"
    # bottom bar is 2 dashes longer to visually match top
    bottom = f"┗{'━' * (len(inner_line) + 2)}┛"
    return top, bottom

