from exchange_client import SimulatedClient, BybitClient
from trade_executor import execute_trade
from account_config import ACCOUNTS

def get_inputs():
    try:
        stop_loss_price = float(input("Enter stop loss price: "))
        risk_percent = float(input("Enter risk %: "))
        leverage = float(input("Enter leverage: "))
        return stop_loss_price, risk_percent, leverage
    except ValueError:
        print("❌ Invalid input.")
        exit(1)

if __name__ == "__main__":
    mode = input("Choose mode (simulate (1) / trade (2)): ").strip().lower()

    if mode in ("simulate", "1"):
        client = SimulatedClient(balance=10000)
        symbol = "BTC/USDT"
    elif mode in ("trade", "2"):
        config = ACCOUNTS[0]  # Choose testnet or real here
        client = BybitClient(config)
        symbol = config["symbol"]
    else:
        print("Invalid mode.")
        exit(1)

    stop_loss_price, risk_percent, leverage = get_inputs()
    execute_trade(client, symbol, stop_loss_price, risk_percent, leverage)
