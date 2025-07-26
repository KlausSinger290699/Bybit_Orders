from account_config import ACCOUNTS
from trade_executor_logic import execute_trade_for_account

symbol = "BTC/USDT"
side = "buy"

risk_percent = float(input("Enter risk % (e.g., 1.5): "))
leverage = float(input("Enter leverage (e.g., 10): "))

if __name__ == "__main__":
    for config in ACCOUNTS:
        execute_trade_for_account(config, risk_percent, leverage, symbol, side)
