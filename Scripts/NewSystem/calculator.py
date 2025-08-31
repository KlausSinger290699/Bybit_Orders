# calculator.py
import order_calculator
from order_calculator import calculate_position_sizing
from models import TradeConfig, TradeParams, OrderPlan
from enums import OrderType
from container import wire_for
from exchange_client import ExchangeClient, DEMO_TRADING
import pyperclip

def header(base, price, balance):
    print(f"\n🧮 {base.upper()} Position Size Calculator")
    print("──────────────────────────────────────────────")
    print(f"📈 {base.upper()} Price      : ${price:,.2f}")
    print(f"💰 Balance           : ${balance:,.2f}")
    print("──────────────────────────────────────────────")

def print_result_simple(result, balance):
    margin = result["margin_required"]
    risk   = result["risk_usdt"]
    print("\n📊 Calculation Result")
    print("──────────────────────────────────────────────")
    print(f"🔒 Margin Required   : ${margin:,.2f}")
    print(f"⚠️  Risk Amount       : ${risk:,.2f}")
    print("──────────────────────────────────────────────")
    if balance is not None and margin > balance:
        print("❌ Margin required exceeds your account balance.")
        print("📋 Nothing was copied to clipboard.")
        return False
    try:
        pyperclip.copy(str(margin))
        print(f"📋 Copied margin required to clipboard: {margin}")
    except Exception:
        pass
    return True

def choose_order_type() -> OrderType:
    print("\nOrder Type:")
    print("1) Market")
    print("2) Limit")
    return OrderType.MARKET if input("Choose (1/2): ").strip() == "1" else OrderType.LIMIT

def main():
    client = ExchangeClient()
    base = input("🔤 Base symbol (e.g., RUNE): ").strip()
    order_type = choose_order_type()

    balance = client.get_balance_usdt()
    live_price = client.get_market_price(base)
    header(base, live_price, balance)

    stop = float(input("🛑 Stop Loss Price   : ").strip())
    lev  = float(input("⚙️  Leverage          : ").strip())
    risk = float(input("⚠️  Risk %            : ").strip())

    if order_type == OrderType.LIMIT:
        entry = float(input("🎯 Entry Price       : ").strip())
    else:
        entry = live_price
        print(f"🎯 Entry Price       : {entry}")

    symbol_full = client.symbol_for(base)

    config = TradeConfig(simulate_mode=DEMO_TRADING, symbol=symbol_full, order_type=order_type)
    params = TradeParams(stop_loss_price=stop, risk_percent=risk, leverage=lev, entry_price=entry)
    wire_for(config, params, modules=[order_calculator])

    result = calculate_position_sizing(balance)
    ok = print_result_simple(result, balance)
    if not ok:
        return

    send = input("\n➡️  Send order to exchange? (y/N): ").strip().lower() == "y"
    if not send:
        return

    side = "buy" if result["direction"] == "long" else "sell"
    amount = result["position_size"]

    plan = OrderPlan(
        symbol=symbol_full,
        order_type=order_type,
        side=side,
        amount=amount,
        stop_loss_price=stop,
        entry_price=entry if order_type == OrderType.LIMIT else None,
        leverage=lev,
    )

    client.apply_leverage(plan)
    resp = client.place_order_with_stop(plan)
    print("✅ Order placed:", resp.get("id", resp))

if __name__ == "__main__":
    main()
