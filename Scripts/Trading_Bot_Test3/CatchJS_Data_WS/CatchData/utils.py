import json

def extract_payload(console_text: str, prefix: str):
    if prefix not in console_text:
        return False, None
    after = console_text.split(prefix, 1)[1].strip()
    if after.startswith("{") or after.startswith("["):
        try:
            return True, json.loads(after)
        except json.JSONDecodeError:
            return True, after
    return True, after


def fmt_tf(sec: int) -> str:
    table = {
        60: "1m", 120: "2m", 180: "3m", 300: "5m", 600: "10m", 900: "15m",
        1200: "20m", 1800: "30m", 3600: "1h", 7200: "2h", 14400: "4h",
        21600: "6h", 43200: "12h", 86400: "1d"
    }
    return table.get(sec, f"{sec}s")


def extract_L1_L2(data: dict):
    piv = data.get("pivots") or {}
    l1 = data.get("L1") or piv.get("L1") or {}
    l2 = data.get("L2") or piv.get("L2") or {}
    return l1, l2


def fmt_price(p):
    if isinstance(p, (int, float)):
        return f"{int(round(p))}"
    return "?"
