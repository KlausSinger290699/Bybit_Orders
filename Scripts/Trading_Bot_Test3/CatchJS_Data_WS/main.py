# your producer script
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.CatchData import playwright_session
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.PreprocessData import bybit_preprocessor, sequence_order
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.SendData import ws_emit_bridge
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.z_Helpers import printer
import atexit

ws_emit_bridge.start_server("127.0.0.1", 8765, logs = False)   # start hub once
atexit.register(ws_emit_bridge.stop)

for raw_data in playwright_session.iter_blocks():
    ordered_raw_data = sequence_order.order_by_l1_time(raw_data)
    printer.print_sequence(ordered_raw_data)
    processed_data = bybit_preprocessor.process(ordered_raw_data)
    printer.print_sequence(processed_data)
    ws_emit_bridge.send(processed_data)          # broadcast to all connected clients
