# input_handler.py
from trading_symbol import TradingSymbol

def choose_mode():
    mode = input("Choose mode (simulate (1) / trade (2)): ").strip().lower()
    if mode not in ("1", "2", "simulate", "trade"):
        print("❌ Invalid mode.")
        exit(1)
    return mode in ("1", "simulate")

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

def get_trade_inputs():
    try:
        stop_loss_price = float(input("Enter stop loss price: "))
        risk_percent = float(input("Enter risk %: "))
        leverage = float(input("Enter leverage: "))
        return stop_loss_price, risk_percent, leverage
    except ValueError:
        print("❌ Invalid input.")
        exit(1)
