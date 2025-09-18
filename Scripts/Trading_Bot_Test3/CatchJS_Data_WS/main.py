from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.SendData import ws_emit_bridge
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.PreprocessData import sequence_store
from Scripts.Trading_Bot_Test3.CatchJS_Data_WS.CatchData import playwright_session


WS_URI = "ws://127.0.0.1:8765"


def main():
    ws_emit_bridge.set_verbose(False)
    ws_emit_bridge.start(WS_URI)
    sequence_store.init_storage()

    p, context, page = playwright_session.open_session()

    try:
        while True:
            page.wait_for_timeout(5_000)
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user.")
    finally:
        sequence_store.flush()
        context.close()
        p.stop()
        ws_emit_bridge.stop()


if __name__ == "__main__":
    main()
