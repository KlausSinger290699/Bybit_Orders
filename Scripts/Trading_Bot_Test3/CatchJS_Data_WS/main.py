import json
from pathlib import Path
from playwright.sync_api import sync_playwright

from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.SendData import ws_emit_bridge
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.CatchData import utils, printer
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.PreprocessData import bybit_preprocessor

# --- CONFIG ---
PREFIX = "[AGGR INDICATOR]"
URL = "https://charts.aggr.trade/koenzv4"
PROFILE_DIR = r"C:\Users\Anwender\PlaywrightProfiles\aggr"
WS_URI = "ws://127.0.0.1:8765"
LOCAL_SAVE = Path("last_payload.json")

# True = show sequences in console; False = print nothing
PRINT_SEQUENCES = True


def main():
    Path(PROFILE_DIR).mkdir(parents=True, exist_ok=True)

    # Quiet websocket logging; we only want sequences in console
    ws_emit_bridge.set_verbose(False)
    ws_emit_bridge.start(WS_URI)

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

            # Preprocess (passthrough for now)
            processed = bybit_preprocessor.handle(payload)

            # Save locally
            LOCAL_SAVE.write_text(json.dumps(processed, indent=2))

            # Send via WebSocket
            ws_emit_bridge.send(processed)

            # Print sequences only
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
