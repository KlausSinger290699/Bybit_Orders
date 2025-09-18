from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.PreprocessData import bybit_preprocessor, sequence_store
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.SendData import ws_emit_bridge
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.CatchData import printer

console = printer.SequencePrinter()

def handle_event(raw: dict):
    """Process → save → send → print."""
    evt = bybit_preprocessor.handle(raw)
    sequence_store.save_event(evt)
    ws_emit_bridge.send(evt)
    console.print_event(evt)
