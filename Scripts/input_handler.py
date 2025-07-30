from enums import TradingSymbol, OrderType

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

def choose_order_type():
    print("Order types:")
    for i, o in enumerate(OrderType, 1):
        print(f"{i}. {o.value}")
    choice = input("Choose order type by number: ").strip()
    try:
        index = int(choice) - 1
        return list(OrderType)[index]
    except (ValueError, IndexError):
        print("❌ Invalid selection.")
        exit(1)

def get_trade_inputs(order_type: OrderType):
    try:
        if order_type == OrderType.LIMIT:
            entry_price = float(input("Enter limit entry price: "))
        else: entry_price = None
        stop_loss_price = float(input("Enter stop loss price: "))
        risk_percent = float(input("Enter risk %: "))
        leverage = float(input("Enter leverage: "))
        return stop_loss_price, risk_percent, leverage, entry_price
    except ValueError:
        print("❌ Invalid input.")
        exit(1)