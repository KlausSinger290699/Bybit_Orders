from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.CatchData import playwright_session, printer
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.PreprocessData import bybit_preprocessor
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.SendData import ws_emit_bridge

for rawdata in playwright_session.iter_blocks():   # ← stream forever
    printer.print_sequence(rawdata)
    processeddata = bybit_preprocessor.process(rawdata)
    #printer.print_sequence(processeddata)
    ws_emit_bridge.send(processeddata)
