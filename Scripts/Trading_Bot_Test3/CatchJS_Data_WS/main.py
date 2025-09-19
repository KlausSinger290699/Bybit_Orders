from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.CatchData import playwright_session
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.PreprocessData import bybit_preprocessor, sequence_order
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.SendData import ws_emit_bridge
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.z_Helpers import printer

for raw_data in playwright_session.iter_blocks():   # ← stream forever
    ordered_raw_data = sequence_order.order_by_l1_time(raw_data)
    printer.print_sequence(ordered_raw_data, tag="Aggr")
    processed_data = bybit_preprocessor.process(ordered_raw_data)
    printer.print_sequence(processed_data, tag = "Bybit")
    ws_emit_bridge.send(processed_data)



# main.py
# from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.CatchData import playwright_session
# from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.PreprocessData import bybit_preprocessor, sequence_order, process_condition
# from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.SendData import ws_emit_bridge
# from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.z_Helpers import printer

# def run():
#     flt = process_condition.BlockChangeFilter(mode="strict")
#     for raw_data in playwright_session.iter_blocks():
#         ordered = sequence_order.order_by_l1_time(raw_data)
#         if not flt.has_changed(ordered): continue
#         flt.remember(ordered)
#         printer.print_sequence(ordered, tag="Aggr")
#         processed = bybit_preprocessor.process(ordered)
#         printer.print_sequence(processed, tag="Bybit")
#         ws_emit_bridge.send(processed)

# if __name__ == "__main__":
#     run()
