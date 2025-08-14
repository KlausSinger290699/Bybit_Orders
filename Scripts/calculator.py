from order_calculator import calculate_position_sizing
from models import TradeConfig, TradeParams
from enums import OrderType

DEFAULT_BALANCE_USDT = 100000
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


def print_result(result):
    print(f"\n📊 Calculation Result")
    print(f"──────────────────────────────────────────────")
    print(f"🔒 Margin Required   : ${result['margin_required']}")
    print(f"⚠️  Risk Amount       : ${result['risk_usdt']}")
    print(f"──────────────────────────────────────────────")


def main():
    balance = get_balance()
    print_header(balance)
    order_type, entry = get_entry_price()
    stop, lev, risk = get_inputs()

    config = TradeConfig(True, f"{ASSET_NAME}USDT", order_type)
    params = TradeParams(
        stop_loss_price=stop,
        risk_percent=risk,
        leverage=lev,
        entry_price=entry
    )

    result = calculate_position_sizing(balance, config=config, params=params)
    print_result(result)


if __name__ == "__main__":
    main()
