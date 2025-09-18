import json
from pathlib import Path
from playwright.sync_api import sync_playwright

from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.SendData import ws_emit_bridge
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.CatchData import utils, printer
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.PreprocessData import bybit_preprocessor, sequence_store

# --- CONFIG ---
PREFIX = "[AGGR INDICATOR]"
URL = "https://charts.aggr.trade/koenzv4"
PROFILE_DIR = r"C:\Users\Anwender\PlaywrightProfiles\aggr"
WS_URI = "ws://127.0.0.1:8765"

PRINT_SEQUENCES = True  # True = show sequences, False = silent console


def main():
    Path(PROFILE_DIR).mkdir(parents=True, exist_ok=True)

    # quiet websocket logs; we only want sequences in console
    ws_emit_bridge.set_verbose(False)
    ws_emit_bridge.start(WS_URI)

    # storage setup (creates data/ and per-run data/sequences_YYYYMMDD_HHMMSS/)
    sequence_store.init_storage()

    console_printer = printer.Printer() if PRINT_SEQUENCES else None

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
        )
        page = context.new_page()

        def on_console(msg):
            try:
                raw = msg.text()
            except Exception:
                raw = str(msg)

            ok, payload = utils.extract_payload(raw, PREFIX)
            if not ok or not isinstance(payload, dict):
                return
            if not utils.is_divergence_event(payload):
                return

            # preprocess (passthrough for now)
            processed = bybit_preprocessor.handle(payload)

            # save single/sequence JSONs
            sequence_store.save_event(processed)

            # forward to websocket
            ws_emit_bridge.send(processed)

            # pretty print (sequences only)
            if console_printer:
                console_printer.add_event(processed)

        page.on("console", on_console)
        page.goto(URL)
        print("🟢 Listening… prefix:", PREFIX)

        try:
            while True:
                page.wait_for_timeout(5_000)
        except KeyboardInterrupt:
            if console_printer:
                console_printer.flush_now()
        finally:
            # flush last buffered sequence to disk
            sequence_store.flush()

            # close browser + ws
            for pge in list(context.pages):
                try:
                    pge.close()
                except Exception:
                    pass
            try:
                context.close()
            except Exception:
                pass
            ws_emit_bridge.stop()


if __name__ == "__main__":
    main()
