from order_calculator import calculate_position_sizing
from models import TradeConfig, TradeParams
from enums import OrderType

# Configuration
DEFAULT_BALANCE_USDT = 100000
ALLOW_CUSTOM_BALANCE = False  # If True, you will be prompted to input balance

# Fake market value (replace later with Bybit API)
ASSET_NAME = "BTC"
FAKE_ASSET_PRICE = 120000

def main():
    print("🧮 Quick Position Size Calculator")
    print(f"📈 {ASSET_NAME} Market Price (Fake): ${FAKE_ASSET_PRICE:,}")

    try:
        # ───────────── Input section ─────────────
        if ALLOW_CUSTOM_BALANCE:
            balance_usdt = float(input("💰 Account Balance (USDT): "))
        else:
            balance_usdt = DEFAULT_BALANCE_USDT

        entry_price = float(input("🎯 Entry Price: "))
        stop_loss_price = float(input("🛑 Stop Loss Price: "))
        leverage = float(input("⚙️  Leverage: "))
        risk_percent = float(input("⚠️  Risk %: "))

        # ───────────── Setup objects ─────────────
        config = TradeConfig(
            simulate_mode=True,
            symbol=f"{ASSET_NAME}USDT",
            order_type=OrderType.MARKET  # Dummy value, ignored
        )

        params = TradeParams(
            entry_price=entry_price,
            stop_loss_price=stop_loss_price,
            leverage=leverage,
            risk_percent=risk_percent
        )

        result = calculate_position_sizing(balance_usdt, config=config, params=params)

        # ───────────── Output ─────────────
        print("\n📊 Trade Calculation:")
        print(f"🔒 Margin Required: ${result['margin_required']}")
        print(f"⚠️  Risk Amount: ${result['risk_usdt']}")
        print(f"📈 Notional Value: ${result['notional_value']}")

    except ValueError as e:
        print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")

if __name__ == "__main__":
    main()
