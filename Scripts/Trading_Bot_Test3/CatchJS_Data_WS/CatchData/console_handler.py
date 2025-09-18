from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.CatchData import utils

def extract_event(msg, prefix="[AGGR INDICATOR]"):
    """Extract and validate a raw event from console, return dict or None."""
    try:
        raw = msg.text()
    except Exception:
        raw = str(msg)

    ok, payload = utils.extract_payload(raw, prefix)
    if not ok or not isinstance(payload, dict):
        return None
    if not utils.is_divergence_event(payload):
        return None
    return payload
