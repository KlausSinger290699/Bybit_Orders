import pyperclip
from datetime import datetime

import order_calculator
import exchange_client as exchange_client_module
from container import wire_for
from enums import OrderType
from exchange_client import ExchangeClient
from models import TradeConfig, TradeParams
from order_calculator import calculate_position_sizing


def hr(title: str = "", i: int = 0):
    t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bar = "═" * 30
    print(f"\n{bar}【 Loop #{i} | {t} 】{bar}" if title else "\n" + "─" * 80)
    if title:
        print(f"🧾 {title}")
        print("─" * (64 + len(str(i))))


def header(base: str, price: float, balance: float, account_name: str | None = None):
    print(f"\n🧮 {base.upper()} Position Size")
    print("──────────────────────────────────────────────")
    if account_name:
        print(f"🧩 Account    : {account_name}")
    print(f"📈 Price      : ${price:,.2f}")
    print(f"💰 Balance    : ${balance:,.2f}")
    print("──────────────────────────────────────────────")


def print_result_simple(result: dict, balance: float | None):
    margin = result["margin_required"]
    risk = result["risk_usdt"]
    lev = result["leverage"]
    order_value = margin * lev
    print("\n📊 Result")
    print("──────────────────────────────────────────────")
    print(f"🔒 Margin     : ${margin:,.2f}   ← copied")
    print(f"🧾 OrderValue : ${order_value:,.2f}  (× {lev:g}x)")
    print(f"⚠️  Risk       : ${risk:,.2f}")
    if balance is not None and margin > balance:
        print("❌ Margin exceeds balance. Nothing copied.")
        return False
    try:
        pyperclip.copy(str(margin))
    except Exception:
        pass
    return True


def choose_order_type(prev: OrderType | None = None) -> OrderType:
    print("\nOrder Type:\n1) Market\n2) Limit")
    raw = input("Choose (1/2): ").strip()
    if raw == "" and prev is not None:
        return prev
    return OrderType.MARKET if raw == "1" else OrderType.LIMIT


def prompt_or_default(prompt: str, prev: str | None = None) -> str:
    raw = input(f"{prompt}: ").strip()
    return prev if raw == "" and prev is not None else raw


def run_once(client: ExchangeClient, i: int, prev: dict):
    hr("START", i)

    base = prompt_or_default("🔤 Base (e.g., RUNE)", prev.get("base"))
    if base.lower() == "q":
        return "quit"

    order_type = choose_order_type(prev.get("order_type"))

    balance = client.get_balance_usdt()
    live_px = client.get_market_price(base)
    header(base, live_px, balance, client.name())

    symbol = client.symbol_for(base)
    stop = float(prompt_or_default("🛑 Stop Loss", f"{prev['stop']}" if "stop" in prev else None))

    lev_input = prompt_or_default("⚙️  Leverage", f"{prev['lev']}" if prev.get("lev") is not None else None)
    if lev_input:
        lev = float(lev_input)
        print(f"⚙️  Leverage    : {lev:g}x")
    else:
        current = client.get_current_leverage(symbol)
        lev = current if current and current > 0 else 1
        print(f"⚙️  Leverage    : {lev:g}x (current/default)")

    risk = float(prompt_or_default("⚠️  Risk %", f"{prev['risk']}" if prev.get("risk") is not None else None))

    if order_type == OrderType.LIMIT:
        entry = float(prompt_or_default("🎯 Entry", f"{prev['entry']}" if prev.get("entry") is not None else None))
    else:
        entry = live_px
        print(f"🎯 Entry      : {entry}")

    trade = TradeConfig(simulate_mode=True, symbol=symbol, order_type=order_type)
    params = TradeParams(stop_loss_price=stop, risk_percent=risk, leverage=lev, entry_price=entry)
    wire_for(trade, params, modules=[order_calculator, exchange_client_module])

    primary_result = client.preview_primary_sizing(balance)
    if not print_result_simple(primary_result, balance):
        hr("END (INSUFFICIENT BALANCE)", i)
        prev.update({"base": base, "order_type": order_type, "lev": lev, "risk": risk, "entry": entry, "stop": stop})
        return

    send = input("\n➡️  Send order? (y/N): ").strip().lower() == "y"
    if not send:
        print("⏭️  Skipped.")
        hr("END (SKIPPED)", i)
        prev.update({"base": base, "order_type": order_type, "lev": lev, "risk": risk, "entry": entry, "stop": stop})
        return

    side = "buy" if primary_result["direction"] == "long" else "sell"
    results = client.submit_all(order_type, side)

    print("\n🚀 Dispatch:")
    for r in results:
        if r.get("ok"):
            print(f" • [{r['name']}] OK  id={r['id']}  amt={r['amount']:.6f}  risk=${r['risk_usd']:,.2f}")
        else:
            print(f" • [{r['name']}] ERR {r['error']}")

    hr("END (OK)", i)
    prev.update({"base": base, "order_type": order_type, "lev": lev, "risk": risk, "entry": entry, "stop": stop})


def main():
    client = ExchangeClient()
    prev: dict = {}
    i = 1
    print("\nTip: type 'q' at Base prompt to quit.")
    try:
        while True:
            try:
                res = run_once(client, i, prev)
                if res == "quit":
                    print("\n👋 Bye.")
                    break
            except ValueError as ve:
                print(f"\n❗ Input error: {ve}")
            except Exception as e:
                print(f"\n💥 Unexpected error: {e}")
            finally:
                i += 1
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted. Exiting.")


if __name__ == "__main__":
    main()
