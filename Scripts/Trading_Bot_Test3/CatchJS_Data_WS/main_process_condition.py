main.py
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.CatchData import playwright_session
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.PreprocessData import bybit_preprocessor, sequence_order, process_condition
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.SendData import ws_emit_bridge
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.z_Helpers import printer

def run():
    flt = process_condition.BlockChangeFilter(mode="strict")
    for raw_data in playwright_session.iter_blocks():
        ordered = sequence_order.order_by_l1_time(raw_data)
        if not flt.has_changed(ordered): continue
        flt.remember(ordered)
        printer.print_sequence(ordered, tag="Aggr")
        processed = bybit_preprocessor.process(ordered)
        printer.print_sequence(processed, tag="Bybit")
        ws_emit_bridge.send(processed)

if __name__ == "__main__":
    run()
