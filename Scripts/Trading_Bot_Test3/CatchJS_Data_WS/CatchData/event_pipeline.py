from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.PreprocessData import bybit_preprocessor, sequence_store
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.SendData import ws_emit_bridge
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.CatchData import printer

_printer = printer.SequencePrinter()  # pretty sequences

def handle_event(raw: dict):
    evt = bybit_preprocessor.process(raw)   # your processing (wraps save)
    sequence_store.save_event(evt)          # keep explicit save to be safe
    ws_emit_bridge.send(evt)                # emit
    _printer.print_event(evt)               # pretty print (processed only)
