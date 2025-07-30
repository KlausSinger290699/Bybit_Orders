from exchange_client import SimulatedClient, BybitClient
from trade_executor import execute_trade
from account_config import ACCOUNTS
from trading_symbol import TradingSymbol

def choose_symbol():
    print("Available symbols:")
    for i, sym in enumerate(TradingSymbol, 1):
        print(f"{i}. {sym.value}")
    choice = input("Choose symbol by number: ").strip()
    try:
        index = int(choice) - 1
        return list(TradingSymbol)[index].value
    except (ValueError, IndexError):
        print("❌ Invalid selection.")
        exit(1)

def get_inputs():
    try:
        stop_loss_price = float(input("Enter stop loss price: "))
        risk_percent = float(input("Enter risk %: "))
        leverage = float(input("Enter leverage: "))
        return stop_loss_price, risk_percent, leverage
    except ValueError:
        print("❌ Invalid input.")
        exit(1)

def build_client(config, simulate_mode):
    if simulate_mode:
        return SimulatedClient(config)
    else:
        return BybitClient(config)

if __name__ == "__main__":
    mode = input("Choose mode (simulate (1) / trade (2)): ").strip().lower()
    simulate_mode = mode in ("simulate", "1")    
    symbol = choose_symbol()

    stop_loss_price, risk_percent, leverage = get_inputs()

for config in ACCOUNTS:
    print(f"\n--- Executing on account: {config['name']} ---")
    client = build_client(config, simulate_mode)
    execute_trade(client, symbol, stop_loss_price, risk_percent, leverage)

