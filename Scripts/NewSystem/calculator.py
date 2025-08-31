import order_calculator
from order_calculator import calculate_position_sizing
from models import TradeConfig, TradeParams
from enums import OrderType
from container import wire_for
from exchange_client import ExchangeClient, DEMO_TRADING
import pyperclip

def choose_mode() -> str:
    print("\nMode:")
    print("1) Calculate only")
    print("2) Calculate and SEND ORDER")
    return "send" if input("Choose (1/2): ").strip() == "2" else "calc"

def choose_order_type() -> OrderType:
    print("\nOrder Type:")
    print("1) Market")
    print("2) Limit")
    return OrderType.MARKET if input("Choose (1/2): ").strip() == "1" else OrderType.LIMIT

def get_base_symbol() -> str:
    return input("🔤 Base symbol (e.g., RUNE): ").strip()

def get_inputs(order_type: OrderType):
    stop = float(input("🛑 Stop Loss Price   : "))
    lev  = float(input("⚙️  Leverage          : "))
    risk = float(input("⚠️  Risk %            : "))
    entry = None
    if order_type == OrderType.LIMIT:
        entry = float(input("🎯 Entry Price       : "))
    return stop, lev, risk, entry

def print_header(symbol_display: str | None, balance: float | None):
    print(f"\n🧮 Position Size Calculator")
    print(f"──────────────────────────────────────────────")
    if symbol_display:
        print(f"📈 Symbol            : {symbol_display}")
    if balance is not None:
        print(f"💰 Balance           : ${balance:,.2f}")
    print(f"──────────────────────────────────────────────")

def print_result(result, balance):
    margin = result['margin_required']
    risk   = result['risk_usdt']

    print(f"\n📊 Calculation Result")
    print(f"──────────────────────────────────────────────")
    print(f"🔒 Margin Required   : ${margin}")
    print(f"⚠️  Risk Amount       : ${risk}")
    print(f"──────────────────────────────────────────────")

    if balance is not None and margin > balance:
        print(f"❌ ERROR: Margin required (${margin}) exceeds your balance (${balance})")
        print(f"🛑 Trade cannot be executed with current leverage and stop loss.")
        print(f"📋 Nothing was copied to clipboard.")
        return False
    else:
        pyperclip.copy(str(margin))
        print(f"📋 Copied margin required to clipboard: {margin}")
        return True

def main():
    client      = ExchangeClient()       # keys + demo trading are owned by the client
    mode        = choose_mode()
    order_type  = choose_order_type()
    base        = get_base_symbol()      # e.g., "rune"
    symbol_full = client.symbol_for(base)

    stop, lev, risk, entry = get_inputs(order_type)

    # Always use API balance; MARKET uses current price for sizing
    balance = client.get_balance_usdt()
    if order_type == OrderType.MARKET:
        entry = client.get_market_price(base)

    print_header(symbol_full, balance)

    # Wire DI for sizing
    config = TradeConfig(simulate_mode=DEMO_TRADING, symbol=symbol_full, order_type=order_type)
    params = TradeParams(stop_loss_price=stop, risk_percent=risk, leverage=lev, entry_price=entry)

    wire_for(config, params, modules=[order_calculator])
    result = calculate_position_sizing(balance)
    ok = print_result(result, balance)

    if mode != "send" or not ok:
        return

    # Place order with SL
    side   = "buy" if result["direction"] == "long" else "sell"
    amount = result["position_size"]

    client.set_leverage(lev, base)
    resp = client.place_order_with_stop(
        order_type=order_type,
        side=side,
        base=base,
        amount=amount,
        stop_loss_price=stop,
        entry_price=entry if order_type == OrderType.LIMIT else None,
        post_only=True
    )
    print("✅ Order placed:", resp.get("id", resp))

if __name__ == "__main__":
    main()
