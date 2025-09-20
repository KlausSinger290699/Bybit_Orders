# main.py
import asyncio
from Scripts.Trading_Bot_Test3.Use_Data_WS.CatchData import ws_receiver_bridge_8765 as recv

if __name__ == "__main__":
    asyncio.run(recv.run("ws://127.0.0.1:8765", noisylogs=True, logs=False))
