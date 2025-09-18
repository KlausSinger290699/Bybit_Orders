import json
SEQ_TARGET_INNER = 58

def extract_payload(console_text: str, prefix: str):
    if prefix not in console_text:
        return False, None
    tail = console_text.split(prefix, 1)[1].strip()
    if tail.startswith("{") or tail.startswith("["):
        try:
            return True, json.loads(tail)
        except json.JSONDecodeError:
            return True, tail
    return True, tail

def is_divergence_event(p: dict) -> bool:
    if not isinstance(p, dict): return False
    if p.get("v") != 1 or p.get("source") != "aggr/indicator": return False
    if not isinstance(p.get("thread_id"), str): return False
    if not isinstance(p.get("sequence"), int): return False
    if not isinstance(p.get("side"), str): return False
    if not isinstance(p.get("status"), str): return False
    l1, l2 = extract_L1_L2(p)
    return isinstance(l1, dict) and isinstance(l2, dict)

def fmt_tf(sec) -> str:
    table = {60:"1m",120:"2m",180:"3m",300:"5m",600:"10m",900:"15m",
             1200:"20m",1800:"30m",3600:"1h",7200:"2h",14400:"4h",
             21600:"6h",43200:"12h",86400:"1d"}
    try:
        return table.get(int(sec), f"{int(sec)}s")
    except Exception:
        return "?"

def fmt_price(p):
    try:
        return f"{int(round(float(p)))}"
    except Exception:
        return "?"

def extract_L1_L2(data: dict):
    if isinstance(data.get("L1"), dict) or isinstance(data.get("L2"), dict):
        return data.get("L1") or {}, data.get("L2") or {}
    piv = data.get("pivots") or {}
    return piv.get("L1") or {}, piv.get("L2") or {}

def to_bold_unicode(s: str) -> str:
    out = []
    for ch in s:
        o = ord(ch)
        if 0x41 <= o <= 0x5A: out.append(chr(0x1D400 + (o - 0x41)))
        elif 0x61 <= o <= 0x7A: out.append(chr(0x1D41A + (o - 0x61)))
        elif 0x30 <= o <= 0x39: out.append(chr(0x1D7CE + (o - 0x30)))
        else: out.append(ch)
    return "".join(out)

def choose_tf_label(batch: list[dict]) -> str:
    for ev in reversed(batch):
        lbl = ev.get("tf_label")
        if lbl: return lbl
        sec = ev.get("tf_sec")
        if sec: return fmt_tf(sec)
    return "?"

def seq_bars(seq_no: int, tf_label: str):
    title = f"📌 {to_bold_unicode('Sequence')} \uFF03{to_bold_unicode(str(seq_no))} — {to_bold_unicode(tf_label)} "
    inner_base = "━━ " + title
    pad = max(0, SEQ_TARGET_INNER - len(inner_base))
    inner = inner_base + ("━" * pad)
    top = f"┏{inner}┓"
    bottom = f"┗{'━' * (len(inner) + 2)}┛"
    return top, bottom
