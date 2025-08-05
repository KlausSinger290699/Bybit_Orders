from enums import TradingSymbol, OrderType
from test_presets import TEST_PRESETS, DEFAULT_TEST_CONFIG

ASK_FOR_DEFAULT = False
USE_DEFAULT = True             # irrelevant when ASK_FOR_DEFAULT = True
SKIP_TEST_SELECTION = True


def init_mode():
    global USE_DEFAULT

    if not ASK_FOR_DEFAULT:
        return

    print("═══════════════════════════════════════════════")
    print("📥 INPUT MODE SELECTION")
    print("═══════════════════════════════════════════════")
    print("1. 🧪 Use default test")
    print("2. 🎛️ Manual input")
    choice = input("Select mode: ").strip()
    USE_DEFAULT = choice == "1"


def is_default():
    return USE_DEFAULT


def get_default_test():
    if SKIP_TEST_SELECTION:
        return DEFAULT_TEST_CONFIG

    print("🔧 Select default test:")
    for i, name in enumerate(TEST_PRESETS, 1):
        print(f"{i}. {name}")
    idx = int(input("Enter number: ").strip()) - 1
    return TEST_PRESETS[list(TEST_PRESETS)[idx]]


def manual_mode():
    print("═══════════════════════════════════════════════")
    print("🎛️ MANUAL MODE CONFIGURATION")
    print("═══════════════════════════════════════════════")
    mode = input("Choose mode (simulate (1) / trade (2)): ").strip().lower()
    simulate_mode = mode in ("1", "simulate")

    print("\n🔀 Available symbols:")
    for i, s in enumerate(TradingSymbol, 1):
        print(f"{i}. {s.value}")
    symbol_index = int(input("Select symbol #: ").strip()) - 1
    symbol = list(TradingSymbol)[symbol_index].value

    print("\n⚙️  Order types:")
    for i, o in enumerate(OrderType, 1):
        print(f"{i}. {o.value}")
    order_type_index = int(input("Select order type #: ").strip()) - 1
    order_type = list(OrderType)[order_type_index]

    return simulate_mode, symbol, order_type


def get_trade_inputs(order_type: OrderType):
    print("\n📥 TRADE PARAMETERS")
    entry_price = None
    if order_type == OrderType.LIMIT:
        entry_price = float(input("📌 Limit entry price: "))
    stop_loss = float(input("🛑 Stop loss price: "))
    risk_percent = float(input("⚠️  Risk %: "))
    leverage = float(input("⚙️  Leverage: "))
    return stop_loss, risk_percent, leverage, entry_price
