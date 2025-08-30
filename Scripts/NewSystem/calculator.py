import order_calculator
from order_calculator import calculate_position_sizing
from models import TradeConfig, TradeParams
from enums import OrderType
from container import wire_for
import pyperclip

DEFAULT_BALANCE_USDT = 200000
ALLOW_CUSTOM_BALANCE = False
FORCE_LIMIT_ORDER = True

ASSET_NAME = "BTC"
FAKE_ASSET_PRICE = 120000


def get_balance():
    if ALLOW_CUSTOM_BALANCE:
        return float(input("💰 Account Balance   : "))
    return DEFAULT_BALANCE_USDT


def get_entry_price():
    if FORCE_LIMIT_ORDER:
        return OrderType.LIMIT, float(input("🎯 Entry Price       : "))

    print("📌 Order Type:\n1. Market (auto)\n2. Limit (manual)")
    if input("Choose (1 or 2): ").strip() == "1":
        print(f"🎯 Entry Price       : using market price (${FAKE_ASSET_PRICE})")
        return OrderType.MARKET, FAKE_ASSET_PRICE

    return OrderType.LIMIT, float(input("🎯 Entry Price       : "))


def get_inputs():
    stop = float(input("🛑 Stop Loss Price   : "))
    lev = float(input("⚙️  Leverage          : "))
    risk = float(input("⚠️  Risk %            : "))
    return stop, lev, risk


def print_header(balance):
    print(f"\n🧮 {ASSET_NAME} Position Size Calculator")
    print(f"──────────────────────────────────────────────")
    print(f"📈 {ASSET_NAME} Price (Fake): ${FAKE_ASSET_PRICE:,}")
    print(f"💰 Balance           : ${balance:,}")
    print(f"──────────────────────────────────────────────")


def print_result(result, balance):
    margin = result['margin_required']
    risk = result['risk_usdt']

    print(f"\n📊 Calculation Result")
    print(f"──────────────────────────────────────────────")
    print(f"🔒 Margin Required   : ${margin}")
    print(f"⚠️  Risk Amount       : ${risk}")
    print(f"──────────────────────────────────────────────")

    if margin > balance:
        print(f"❌ ERROR: Margin required (${margin}) exceeds your balance (${balance})")
        print(f"🛑 Trade cannot be executed with current leverage and stop loss.")
        print(f"📋 Nothing was copied to clipboard.")
    else:
        pyperclip.copy(str(margin))
        print(f"📋 Copied margin required to clipboard: {margin}")


def main():
    balance = get_balance()
    print_header(balance)
    stop, lev, risk = get_inputs()
    order_type, entry = get_entry_price()

    config = TradeConfig(True, f"{ASSET_NAME}USDT", order_type)
    params = TradeParams(
        stop_loss_price=stop,
        risk_percent=risk,
        leverage=lev,
        entry_price=entry
    )

    wire_for(config, params, modules=[order_calculator])
    result = calculate_position_sizing(balance)
    print_result(result, balance)

if __name__ == "__main__":
    main()
