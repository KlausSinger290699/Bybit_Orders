from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.CatchData import utils
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.CatchData import event_pipeline

def on_console(msg, prefix="[AGGR INDICATOR]"):
    try:
        raw_text = msg.text()
    except Exception:
        raw_text = str(msg)

    ok, payload = utils.extract_payload(raw_text, prefix)
    if not ok or not isinstance(payload, dict):
        return
    if not utils.is_divergence_event(payload):
        return

    # process → save → send → print (processed only)
    event_pipeline.handle_event(payload)
