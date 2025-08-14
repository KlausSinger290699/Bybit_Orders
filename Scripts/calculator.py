from order_calculator import calculate_position_sizing
from models import TradeConfig, TradeParams
from enums import OrderType

DEFAULT_BALANCE_USDT = 100000
ALLOW_CUSTOM_BALANCE = False

ASSET_NAME = "BTC"
FAKE_ASSET_PRICE = 120000

def main():
    print(f"\n🧮 {ASSET_NAME} Position Size Calculator")
    print(f"──────────────────────────────────────────────")
    print(f"📈 {ASSET_NAME} Price (Fake): ${FAKE_ASSET_PRICE:,}")

    if ALLOW_CUSTOM_BALANCE:
        balance_usdt = float(input("💰 Account Balance   : "))
    else:
        balance_usdt = DEFAULT_BALANCE_USDT
        print(f"💰 Balance           : ${balance_usdt:,}")

    print(f"──────────────────────────────────────────────")
    entry_price = float(input("🎯 Entry Price       : "))
    stop_loss_price = float(input("🛑 Stop Loss Price   : "))
    leverage = float(input("⚙️  Leverage          : "))
    risk_percent = float(input("⚠️  Risk %            : "))

    config = TradeConfig(
        simulate_mode=True,
        symbol=f"{ASSET_NAME}USDT",
        order_type=OrderType.MARKET
    )

    params = TradeParams(
        stop_loss_price=stop_loss_price,
        risk_percent=risk_percent,
        leverage=leverage,
        entry_price=entry_price
    )

    result = calculate_position_sizing(balance_usdt, config=config, params=params)

    print(f"\n📊 Calculation Result")
    print(f"──────────────────────────────────────────────")
    print(f"🔒 Margin Required   : ${result['margin_required']}")
    print(f"⚠️  Risk Amount       : ${result['risk_usdt']}")
    print(f"📈 Notional Value    : ${result['notional_value']}")
    print(f"──────────────────────────────────────────────")

if __name__ == "__main__":
    main()
