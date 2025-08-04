from enums import TradingSymbol, OrderType

# Set this to False to use interactive/manual input
USE_DEFAULT_INPUTS = False

# Define your presets here
DEFAULT_TESTS = {
    "quick_btc_market": {
        "simulate_mode": True,
        "symbol": TradingSymbol.BTC.value,
        "order_type": OrderType.MARKET,
        "entry_price": None,
        "stop_loss_price": 46000.0,
        "risk_percent": 1.0,
        "leverage": 10.0
    },
    "eth_limit_test": {
        "simulate_mode": True,
        "symbol": TradingSymbol.ETH.value,
        "order_type": OrderType.LIMIT,
        "entry_price": 3100.0,
        "stop_loss_price": 2900.0,
        "risk_percent": 2.0,
        "leverage": 5.0
    }
}


def get_selected_default_test():
    print("🔧 Select default test:")
    for i, key in enumerate(DEFAULT_TESTS, 1):
        print(f"{i}. {key}")
    try:
        idx = int(input("Enter number: ").strip()) - 1
        return DEFAULT_TESTS[list(DEFAULT_TESTS)[idx]]
    except (ValueError, IndexError):
        print("❌ Invalid selection.")
        exit(1)


# --- Only used when USE_DEFAULT_INPUTS = False ---
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
        else:
            entry_price = None
        stop_loss_price = float(input("Enter stop loss price: "))
        risk_percent = float(input("Enter risk %: "))
        leverage = float(input("Enter leverage: "))
        return stop_loss_price, risk_percent, leverage, entry_price
    except ValueError:
        print("❌ Invalid input.")
        exit(1)
