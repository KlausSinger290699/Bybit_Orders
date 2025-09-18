import json
from pathlib import Path
from playwright.sync_api import sync_playwright

from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.SendData import ws_emit_bridge
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.CatchData import utils, printer, strategy_engine
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.PreprocessData import preprocessor

# --- CONFIG ---
PREFIX = "[AGGR INDICATOR]"
URL = "https://charts.aggr.trade/koenzv4"
PROFILE_DIR = r"C:\Users\Anwender\PlaywrightProfiles\aggr"
WS_URI = "ws://127.0.0.1:8765"
LOCAL_SAVE = Path("last_payload.json")


def main():
    Path(PROFILE_DIR).mkdir(parents=True, exist_ok=True)
    ws_emit_bridge.start(WS_URI)

    console_printer = printer.Printer()
    engine = strategy_engine.StrategyEngine()

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

            # 1) Preprocess
            processed = preprocessor.handle(payload)

            # 2) Save locally
            LOCAL_SAVE.write_text(json.dumps(processed, indent=2))

            # 3) Send via WebSocket
            ws_emit_bridge.send(processed)

            # 4) (optional) print + strategy
            engine.on_event(processed)
            console_printer.add_event(processed)

        page.on("console", on_console)
        page.goto(URL)
        print("🟢 Listening… prefix:", PREFIX)

        try:
            while True:
                page.wait_for_timeout(5_000)
        except KeyboardInterrupt:
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
