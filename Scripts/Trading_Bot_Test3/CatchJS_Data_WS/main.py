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
    ws_emit_bridge.set_verbose(False)
    ws_emit_bridge.start(WS_URI)
    sequence_store.init_storage()

    console_printer = printer.SequencePrinter() if PRINT_SEQUENCES else None

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

            processed = bybit_preprocessor.handle(payload)
            sequence_store.save_event(processed)
            ws_emit_bridge.send(processed)

            if console_printer:
                seq_id = processed.get("sequence")
                tf_label = utils._choose_tf_label([processed])

                # If a new sequence starts, close the old one before printing new header
                if seq_id != console_printer.current_seq_id:
                    console_printer.end_if_open()
                    console_printer.start(seq_id, tf_label)

                # Print the line (auto-closes on Nth line if needed)
                console_printer.add(processed)

        page.on("console", on_console)
        page.goto(URL)
        print("🟢 Listening… prefix:", PREFIX)

        try:
            while True:
                page.wait_for_timeout(5_000)
        except KeyboardInterrupt:
            if console_printer:
                console_printer.end_if_open()
        finally:
            sequence_store.flush()
            if console_printer:
                console_printer.end_if_open()
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
