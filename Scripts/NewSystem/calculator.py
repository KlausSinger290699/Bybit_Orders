import order_calculator
from order_calculator import calculate_position_sizing
from models import TradeConfig, TradeParams
from enums import OrderType, TradingSymbol
from container import wire_for
from exchange_client import ExchangeClient
import pyperclip

# ===== Config toggles =====
ALLOW_CUSTOM_BALANCE = False  # ignored if you choose "Send Order" (API balance used)
TESTNET = True                # set False for live
API_KEY = None                # or set env BYBIT_API_KEY
API_SECRET = None             # or set env BYBIT_API_SECRET

def choose_symbol() -> str:
    print("\n📌 Symbol choices:")
    for i, sym in enumerate(TradingSymbol, start=1):
        print(f"{i}. {sym.value}")
    val = input("Choose (number) or type a symbol (e.g., BTC/USDT:USDT): ").strip()
    if val.isdigit():
        idx = int(val) - 1
        all_syms = list(TradingSymbol)
        if 0 <= idx < len(all_syms):
            return all_syms[idx].value
    return val if val else TradingSymbol.BTC.value

def choose_action() -> str:
    print("\nMode:")
    print("1) Calculate only")
    print("2) Calculate and SEND ORDER")
    return "send" if input("Choose (1/2): ").strip() == "2" else "calc"

def choose_order_type() -> OrderType:
    print("\nOrder Type:")
    print("1) Market")
    print("2) Limit")
    return OrderType.MARKET if input("Choose (1/2): ").strip() == "1" else OrderType.LIMIT

def get_balance_manual(default_balance=200000) -> float:
    if ALLOW_CUSTOM_BALANCE:
        return float(input("💰 Account Balance   : "))
    return default_balance

def get_inputs(order_type: OrderType):
    stop = float(input("🛑 Stop Loss Price   : "))
    lev  = float(input("⚙️  Leverage          : "))
    risk = float(input("⚠️  Risk %            : "))
    entry = None
    if order_type == OrderType.LIMIT:
        entry = float(input("🎯 Entry Price       : "))
    return stop, lev, risk, entry

def print_header(symbol: str, balance: float | None):
    print(f"\n🧮 Position Size Calculator")
    print(f"──────────────────────────────────────────────")
    print(f"📈 Symbol            : {symbol}")
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
    symbol       = choose_symbol()
    mode         = choose_action()
    order_type   = choose_order_type()
    stop, lev, risk, entry = get_inputs(order_type)

    # If sending orders, pull real balance via API; else, local/manual
    client = None
    if mode == "send":
        client = ExchangeClient(API_KEY, API_SECRET, testnet=TESTNET)
        balance = client.get_balance_usdt()
    else:
        balance = get_balance_manual()

    print_header(symbol, balance)

    config = TradeConfig(simulate_mode=TESTNET, symbol=symbol, order_type=order_type)
    params = TradeParams(stop_loss_price=stop, risk_percent=risk, leverage=lev, entry_price=entry or 0.0)

    # Wire DI and calculate
    wire_for(config, params, modules=[order_calculator])
    result = calculate_position_sizing(balance)
    ok = print_result(result, balance)

    if mode != "send" or not ok:
        return

    # --- Place order with stop-loss ---
    # direction -> side
    side = "buy" if result["direction"] == "long" else "sell"
    amount = result["position_size"]

    # set leverage (best effort)
    client.set_leverage(params.leverage, symbol)

    if order_type == OrderType.MARKET:
        resp = client.market_order_with_sl(symbol, side, amount, stop_loss_price=params.stop_loss_price)
        print("✅ Market+SL placed:", resp.get("id", resp))
    else:
        entry_price = float(params.entry_price)
        resp = client.limit_order_with_sl(symbol, side, amount, entry_price, stop_loss_price=params.stop_loss_price, post_only=True)
        print("✅ Limit+SL placed:", resp.get("id", resp))

if __name__ == "__main__":
    main()
