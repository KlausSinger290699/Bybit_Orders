from container import Container
from input_handler import (
    init_mode, is_default, get_default_test,
    manual_mode, get_trade_inputs
)
from trade_executor import execute_trade
from exchange_client import SimulatedClient, BybitClient
from account_config import ACCOUNTS


def get_config():
    if is_default():
        t = get_default_test()
        return t["simulate_mode"], t["symbol"], t["order_type"], t
    mode, symbol, order_type = manual_mode()
    return mode, symbol, order_type, None


def preview(symbol, simulate):
    rows = []
    for acc in ACCOUNTS:
        client = SimulatedClient(acc) if simulate else BybitClient(acc)
        name = acc["name"]
        balance = client.get_balance_usdt()
        risk = round(balance * 0.01, 2)
        rows.append((name, balance, risk))

    price_client = SimulatedClient(ACCOUNTS[0]) if simulate else BybitClient(ACCOUNTS[0])
    price = price_client.get_market_price(symbol)

    print("\n═══════════════════════════════════════════════")
    print("📊  ACCOUNT OVERVIEW")
    print("═══════════════════════════════════════════════")

    for name, balance, risk in rows:
        print(f"💼 {name:<15} | 💰 Balance: ${balance:>9,.2f} | ⚠️  1% Risk: ${risk:>7,.2f}")

    print("───────────────────────────────────────────────")
    print(f"📈 {symbol} Price: ${price}")
    print("═══════════════════════════════════════════════")



def setup() -> Container:
    mode, symbol, otype, preset = get_config()
    preview(symbol, mode)
    if preset:
        sl, risk, lev, entry = (
            preset["stop_loss_price"], preset["risk_percent"],
            preset["leverage"], preset["entry_price"]
        )
    else:
        sl, risk, lev, entry = get_trade_inputs(otype)

    container = Container()
    container.config.simulate_mode.from_value(mode)
    container.config.symbol.from_value(symbol)
    container.config.order_type.from_value(otype)
    container.config.stop_loss_price.from_value(sl)
    container.config.risk_percent.from_value(risk)
    container.config.leverage.from_value(lev)
    container.config.entry_price.from_value(entry)
    container.wire(modules=["trade_executor", "order_calculator"])
    return container


def run(container: Container):
    cfg = container.trade_config()
    for acc in ACCOUNTS:
        print(f"\n--- Executing on: {acc['name']} ---")
        client = SimulatedClient(acc) if cfg.simulate_mode else BybitClient(acc)
        execute_trade(client)


if __name__ == "__main__":
    init_mode()
    print("\n🧪 Default Mode\n" if is_default() else "\n🎛️ Manual Mode\n")
    run(setup())
