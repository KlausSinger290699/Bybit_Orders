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

def header(ticker: str | None, price: float, balance: float, account_name: str | None = None):
    print("\n──────────────────────────────────────────────")
    if ticker:
        print(f"🧮 {ticker.upper()}")
    if account_name:
        print(f"🧩 Account    : {account_name}")
    print(f"📈 Price      : ${price:,.2f}")
    print(f"💰 Balance    : ${balance:,.2f}")
    print("──────────────────────────────────────────────")

def print_result_simple(result: dict, balance: float | None):
    margin = result["margin_required"]; risk = result["risk_usdt"]; lev = result["leverage"]
    order_value = margin * lev
    print("\n📊 Result")
    print("──────────────────────────────────────────────")
    print(f"🔒 Margin     : ${margin:,.2f}   ← copied")
    print(f"🧾 OrderValue : ${order_value:,.2f}  (× {lev:g}x)")
    print(f"⚠️  Risk       : ${risk:,.2f}")
    if balance is not None and margin > balance:
        print("❌ Margin exceeds balance. Nothing copied.")
        return False
    try: pyperclip.copy(str(margin))
    except Exception: pass
    return True

def prompt_or_default(prompt: str, prev: str | None = None) -> str:
    raw = input(f"{prompt}: ").strip()
    return prev if raw == "" and prev is not None else raw

# -------- MANAGE ORDERS (no ticker needed) --------
def manage_orders(client: ExchangeClient, i: int):
    hr("MANAGE ORDERS", i)
    print("\nActions:\n1) Cancel ours\n2) Cancel all\n3) Cancel key\n4) Close all positions")
    choice = input("Choose (1/2/3/4) or type: cancel ours | cancel all | key <ID> | close all: ").strip()
    lower = choice.lower()
    symbol = None  # operate across all symbols
    if choice == "1" or lower == "cancel ours":
        res = client.cancel_all_ours(symbol); print("\n🧹 Cancel ours:")
        for r in res: print(f" • [{r['name']}] {'OK' if r.get('ok') else 'ERR'}")
    elif choice == "2" or lower == "cancel all":
        res = client.cancel_all_everywhere(symbol); print("\n🧹 Cancel ALL open orders:")
        for r in res: print(f" • [{r['name']}] {'OK' if r.get('ok') else 'ERR'}")
    elif choice == "3" or lower.startswith("key "):
        key = choice.split(" ",1)[1].strip() if lower.startswith("key ") else input("Order ID: ").strip()
        if not key: print("⚠️  Provide an order id or clientOrderId.")
        else:
            res = client.cancel_specific_everywhere(key, symbol); print("\n🧹 Cancel by key:")
            for r in res: print(f" • [{r['name']}] {'OK' if r.get('ok') else 'ERR'}")
    elif choice == "4" or lower == "close all":
        res = client.close_all_positions(symbol); print("\n🧨 Close ALL positions (reduce-only):")
        for r in res: print(f" • [{r['name']}] {'OK' if r.get('ok') else 'ERR'}")
    else:
        print("⚠️  Unknown choice.")
    hr("END (OPS)", i)

# -------- TRADE (now includes Pyramid as option 3) --------
def trade_or_pyramid(client: ExchangeClient, i: int, prev: dict):
    hr("START", i)
    ticker = prompt_or_default("🔤 Ticker", prev.get("ticker"))
    if ticker.lower() == "q": return "quit"
    balance = client.get_balance_usdt()
    live_px = client.get_market_price(ticker)
    header(ticker, live_px, balance, client.name())
    symbol = client.symbol_for(ticker)

    # choose action inside Trade
    print("\n📦 Trade:\n1) Market\n2) Limit\n3) Pyramid")
    mode = input("Choose (1/2/3): ").strip()

    # shared inputs
    stop = float(prompt_or_default("🛑 Stop loss", f"{prev['stop']}" if "stop" in prev else None))
    lev_in = prompt_or_default("⚙️  Leverage (Enter=current)", f"{prev['lev']}" if prev.get("lev") is not None else None)
    if lev_in:
        lev = float(lev_in); print(f"⚙️  Leverage    : {lev:g}x")
    else:
        current = client.get_current_leverage(symbol); lev = current if current and current > 0 else 1
        print(f"⚙️  Leverage    : {lev:g}x (current/default)")

    if mode == "3":
        # -------- Pyramid flow --------
        risk = float(prompt_or_default("⚠️  Total risk %", f"{prev['pyr_risk']}" if prev.get("pyr_risk") is not None else None))
        top_raw = prompt_or_default("⛰️  Top price (Enter=live)", f"{prev['pyr_top']}" if prev.get("pyr_top") is not None else None)
        top = float(top_raw) if top_raw else None
        bottom = float(prompt_or_default("⛰️  Bottom price", f"{prev['pyr_bottom']}" if prev.get("pyr_bottom") is not None else None))
        levels = int(float(prompt_or_default("📐 # of LIMIT levels", f"{prev['pyr_levels']}" if prev.get("pyr_levels") is not None else None)))
        imm    = float(prompt_or_default("⚡ Immediate fill %", f"{prev['pyr_imm']}" if prev.get("pyr_imm") is not None else "0"))
        shape_raw = prompt_or_default("📈 Risk shape (0=square, 1=pyramid)", f"{prev['pyr_shape']}" if prev.get("pyr_shape") is not None else "1")
        risk_shape = float(shape_raw) if shape_raw != "" else 1.0

        from order_calculator import plan_pyramid_tranches
        plan = plan_pyramid_tranches(
            balance_usdt=balance,
            risk_percent=risk,
            stop_price=stop,
            leverage=lev,
            top_price=top,
            bottom_price=bottom,
            live_price=live_px,
            levels=levels,
            immediate_risk_pct=imm,
            risk_shape=risk_shape,
        )
        print("\n📊 Pyramid Preview (Primary)")
        print("──────────────────────────────────────────────")
        print(f"📐 Side        : {plan['side'].upper()}")
        print(f"🔒 Margin     : ${plan['totals']['margin']:,.2f}")
        print(f"🧾 OrderValue : ${plan['totals']['notional']:,.2f}  (× {lev:g}x)")
        print(f"⚠️  Risk total : ${plan['totals']['risk']:,.2f}")
        print(f"📈 Shape      : {plan['meta']['risk_shape']:.2f} (0=square, 1=pyramid)")
        print(f"📦 Tranches   : {len(plan['tranches'])} (imm={imm:.2f}% + {levels} limits)")

        send = input("\n➡️  Send pyramid? (y/N): ").strip().lower() == "y"
        if not send:
            print("⏭️  Skipped."); hr("END (SKIPPED)", i)
            prev.update({
                "ticker": ticker, "pyr_stop": stop, "pyr_lev": lev, "pyr_risk": risk,
                "pyr_top": top if top is not None else "", "pyr_bottom": bottom,
                "pyr_levels": levels, "pyr_imm": imm, "pyr_shape": risk_shape, "stop": stop, "lev": lev
            })
            return

        results = client.submit_pyramid(
            base=ticker,
            stop_price=stop,
            leverage=lev,
            risk_percent=risk,
            top_price=top,
            bottom_price=bottom,
            levels=levels,
            immediate_risk_pct=imm,
            post_only_limits=True,
            risk_shape=risk_shape,
        )
        print("\n🚀 Pyramid Dispatch:")
        for r in results:
            if r.get("ok"):
                t = r["totals"]
                print(f" • [{r['name']}] OK  side={r['side']}  risk=${t['risk']:,.2f}  value=${t['notional']:,.2f}  margin=${t['margin']:,.2f}  levels={r['levels']}  imm={r['immediate_pct']}%  shape={r.get('shape', 1.0)}")
            else:
                print(f" • [{r['name']}] ERR {r.get('error')}")
        hr("END (OK)", i)
        prev.update({
            "ticker": ticker, "pyr_stop": stop, "pyr_lev": lev, "pyr_risk": risk,
            "pyr_top": top if top is not None else "", "pyr_bottom": bottom,
            "pyr_levels": levels, "pyr_imm": imm, "pyr_shape": risk_shape,
            "stop": stop, "lev": lev
        })
        return

    # -------- Single trade (Market/Limit) --------
    risk = float(prompt_or_default("⚠️  Risk %", f"{prev['risk']}" if prev.get("risk") is not None else None))
    order_type = OrderType.MARKET if mode == "1" else OrderType.LIMIT
    if order_type == OrderType.LIMIT:
        entry = float(prompt_or_default("🎯 Entry", f"{prev['entry']}" if prev.get("entry") is not None else None))
    else:
        entry = live_px; print(f"🎯 Entry      : {entry}")

    trade = TradeConfig(simulate_mode=True, symbol=symbol, order_type=order_type)
    params = TradeParams(stop_loss_price=stop, risk_percent=risk, leverage=lev, entry_price=entry)
    wire_for(trade, params, modules=[order_calculator, exchange_client_module])

    primary_result = client.preview_primary_sizing(balance)
    if not print_result_simple(primary_result, balance):
        hr("END (INSUFFICIENT BALANCE)", i)
        prev.update({"ticker": ticker, "order_type": order_type, "lev": lev, "risk": risk, "entry": entry, "stop": stop})
        return

    send = input("\n➡️  Send order? (y/N): ").strip().lower() == "y"
    if not send:
        print("⏭️  Skipped."); hr("END (SKIPPED)", i)
        prev.update({"ticker": ticker, "order_type": order_type, "lev": lev, "risk": risk, "entry": entry, "stop": stop}); return

    side = "buy" if primary_result["direction"] == "long" else "sell"
    results = client.submit_all(order_type, side)
    print("\n🚀 Dispatch:")
    for r in results:
        print(f" • [{r['name']}] {'OK' if r.get('ok') else 'ERR'}", end="")
        if r.get("ok"): print(f"  id={r['id']}  amt={r['amount']:.6f}  risk=${r['risk_usd']:,.2f}")
        else: print(f"  {r.get('error')}")
    hr("END (OK)", i)
    prev.update({"ticker": ticker, "order_type": order_type, "lev": lev, "risk": risk, "entry": entry, "stop": stop})

def main():
    client = ExchangeClient()
    prev: dict = {}
    i = 1
    print("\nTip: type 'q' to quit.")
    try:
        while True:
            try:
                print("\n⚙️ Mode:\n1) Trade\n2) Manage orders")
                mode = input("Choose (1/2): ").strip()
                if mode == "2":
                    manage_orders(client, i)
                else:
                    res = trade_or_pyramid(client, i, prev)
                    if res == "quit": print("\n👋 Bye."); break
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
