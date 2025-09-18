from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.SendData import ws_emit_bridge
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.PreprocessData import sequence_store
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.CatchData import event_pipeline, playwright_session, console_handler

WS_URI = "ws://127.0.0.1:8765"

def main():
    ws_emit_bridge.set_verbose(False)
    ws_emit_bridge.start(WS_URI)
    sequence_store.init_storage()

    playwright, context, page = playwright_session.open_session()

    def on_console(msg):
        raw = console_handler.extract_event(msg)
        if raw:
            event_pipeline.handle_event(raw)

    page.on("console", on_console)

    try:
        while True:
            page.wait_for_timeout(5_000)
    finally:
        sequence_store.flush()
        context.close()
        playwright.stop()
        ws_emit_bridge.stop()

if __name__ == "__main__":
    main()
