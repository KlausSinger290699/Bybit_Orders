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

    console = printer.SequencePrinter() if PRINT_SEQUENCES else None

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

            evt = bybit_preprocessor.handle(payload)
            sequence_store.save_event(evt)
            ws_emit_bridge.send(evt)

            if console:
                seq_id = evt.get("sequence")
                tf_label = utils.choose_tf_label([evt])

                # if sequence changes, close previous before printing new header
                if seq_id != console.current_seq_id:
                    console.end_if_open()
                    console.start(seq_id, tf_label)

                console.add(evt)

        page.on("console", on_console)
        page.goto(URL)
        print("🟢 Listening… prefix:", PREFIX)

        try:
            while True:
                page.wait_for_timeout(5_000)
        except KeyboardInterrupt:
            pass
        finally:
            if console:
                console.end_if_open()
            sequence_store.flush()
            # close browser cleanly
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
