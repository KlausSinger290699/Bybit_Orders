from order_simulator import run_simulation
from trade_executor_logic import run_trading

if __name__ == "__main__":
    mode = input("Choose mode (simulate/trade): ").strip().lower()
    if mode == "simulate":
        run_simulation()
    elif mode == "trade":
        run_trading()
    else:
        print("Invalid mode. Use 'simulate' or 'trade'.")
