from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.CatchData import utils, printer
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.PreprocessData import bybit_preprocessor, sequence_store
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.SendData import ws_emit_bridge

console = printer.SequencePrinter()

def handle_message(msg, prefix="[AGGR INDICATOR]"):
    try:
        raw = msg.text()
    except Exception:
        raw = str(msg)

    ok, payload = utils.extract_payload(raw, prefix)
    if not ok or not isinstance(payload, dict):
        return
    if not utils.is_divergence_event(payload):
        return

    evt = bybit_preprocessor.handle(payload)
    sequence_store.save_event(evt)
    ws_emit_bridge.send(evt)
    console.print_event(evt)
