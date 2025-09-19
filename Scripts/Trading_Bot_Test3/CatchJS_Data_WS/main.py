from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.CatchData import playwright_session, printer
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.PreprocessData import bybit_preprocessor, sequence_order
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.SendData import ws_emit_bridge

for raw_data in playwright_session.iter_blocks():   # ← stream forever
    ordered_raw_data = sequence_order.order_by_l1_time(raw_data)
    printer.print_sequence(ordered_raw_data, tag="Aggr")
    processed_data = bybit_preprocessor.process(ordered_raw_data)
    printer.print_sequence(processed_data, tag = "Bybit")
    ws_emit_bridge.send(processed_data)
