from trade_executor import execute_trade
from real_bybit_client import RealBybitClient
from simulated_client import SimulatedClient
from account_config import ACCOUNTS

def main():
    mode = input("Choose mode (simulate / trade): ").strip().lower()

    try:
        entry = float(input("Entry price: "))
        stop = float(input("Stop loss price: "))
        risk = float(input("Risk %: "))
        lev = float(input("Leverage: "))
    except ValueError:
        print("❌ Invalid input.")
        return

    symbol = "BTC/USDT"

    if mode == "simulate":
        client = SimulatedClient(balance=10000)
        execute_trade(client, entry, stop, risk, lev, symbol)

    elif mode == "trade":
        for config in ACCOUNTS:
            client = RealBybitClient(config)
            execute_trade(client, entry, stop, risk, lev, config["symbol"])
    else:
        print("❌ Invalid mode.")

if __name__ == "__main__":
    main()
