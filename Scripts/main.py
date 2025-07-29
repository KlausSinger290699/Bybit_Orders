from order_simulator import run_simulation
from trade_executor_logic import run_trading

use_presets = True,

if __name__ == "__main__":
    mode = input("Choose mode (simulate (1) / trade (2)): ").strip().lower()
    if mode in ("simulate", "1"):
        run_simulation(use_presets)
    elif mode in ("trade", "2"):
        run_trading()
    else:
        print("Invalid mode. Use 'simulate' or 'trade'.")
