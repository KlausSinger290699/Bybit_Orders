from enums import TradingSymbol, OrderType
from test_presets import TEST_PRESETS


ASK_FOR_DEFAULT = True
USE_DEFAULT = False


def init_mode():
    global USE_DEFAULT
    if not ASK_FOR_DEFAULT:
        USE_DEFAULT = True
        return
    print("1. 🧪 Use default test\n2. 🎛️ Manual input")
    USE_DEFAULT = input("Select mode: ").strip() == "1"


def is_default(): return USE_DEFAULT


def get_default_test():
    print("🔧 Select default test:")
    for i, name in enumerate(TEST_PRESETS, 1):
        print(f"{i}. {name}")
    idx = int(input("Enter number: ")) - 1
    return TEST_PRESETS[list(TEST_PRESETS)[idx]]


def manual_mode():
    simulate_mode = input("Simulate (1) / Trade (2): ").strip() in ("1", "simulate")
    print("Available symbols:")
    for i, s in enumerate(TradingSymbol, 1): print(f"{i}. {s.value}")
    symbol = list(TradingSymbol)[int(input("Symbol #: ")) - 1].value
    print("Order types:")
    for i, o in enumerate(OrderType, 1): print(f"{i}. {o.value}")
    order_type = list(OrderType)[int(input("Order type #: ")) - 1]
    return simulate_mode, symbol, order_type


def get_trade_inputs(order_type: OrderType):
    entry = float(input("Limit entry price: ")) if order_type == OrderType.LIMIT else None
    sl = float(input("Stop loss price: "))
    risk = float(input("Risk %: "))
    lev = float(input("Leverage: "))
    return sl, risk, lev, entry
