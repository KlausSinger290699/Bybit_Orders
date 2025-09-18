from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.SendData import ws_emit_bridge
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.PreprocessData import sequence_store, bybit_preprocessor
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.CatchData import playwright_session, console_handler, printer


WS_URI = "ws://127.0.0.1:8765"
PRINT_SEQUENCES = True


def main():
    ws_emit_bridge.set_verbose(False)
    ws_emit_bridge.start(WS_URI)
    sequence_store.init_storage()
    console = printer.SequencePrinter() if PRINT_SEQUENCES else None

    playwright, context, page = playwright_session.open_session()

    def on_console(msg):
        raw = console_handler.extract_event(msg)
        if not raw:
            return

        # Pretty print raw
        if console:
            console.print_event(raw)

        # Process + send
        evt = bybit_preprocessor.handle(raw)
        sequence_store.save_event(evt)
        ws_emit_bridge.send(evt)

        # Pretty print processed
        if console:
            console.print_event(evt)

    # Hook event handler back in
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
