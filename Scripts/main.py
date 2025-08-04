from container import Container
from input_handler import (
    init_input_mode,
    is_using_default_inputs,
    get_selected_default_test,
    choose_mode,
    choose_symbol,
    choose_order_type,
    get_trade_inputs,
)
from trade_executor import execute_trade
from exchange_client import SimulatedClient, BybitClient
from account_config import ACCOUNTS


def collect_user_config():
    if is_using_default_inputs():
        test = get_selected_default_test()
        return test["simulate_mode"], test["symbol"], test["order_type"], test
    simulate_mode = choose_mode()
    symbol = choose_symbol()
    order_type = choose_order_type()
    return simulate_mode, symbol, order_type, None


def display_trade_preview_info(symbol, simulate_mode):
    preview_client = SimulatedClient(ACCOUNTS[0]) if simulate_mode else BybitClient(ACCOUNTS[0])
    price = preview_client.get_market_price(symbol)
    balance = preview_client.get_balance_usdt()
    estimated_risk = round(balance * 0.01, 2)
    print(f"\n💰 Account balance: ${balance:.2f}")
    print(f"⚠️ Estimated 1% risk: ${estimated_risk:.2f}")
    print(f"📊 Current price for {symbol}: ${price}")


def setup_container() -> Container:
    simulate_mode, symbol, order_type, default_test = collect_user_config()
    display_trade_preview_info(symbol, simulate_mode)
    if default_test:
        stop_loss_price = default_test["stop_loss_price"]
        risk_percent = default_test["risk_percent"]
        leverage = default_test["leverage"]
        entry_price = default_test["entry_price"]
    else:
        stop_loss_price, risk_percent, leverage, entry_price = get_trade_inputs(order_type)
    container = Container()
    container.config.simulate_mode.from_value(simulate_mode)
    container.config.symbol.from_value(symbol)
    container.config.order_type.from_value(order_type)
    container.config.stop_loss_price.from_value(stop_loss_price)
    container.config.risk_percent.from_value(risk_percent)
    container.config.leverage.from_value(leverage)
    container.config.entry_price.from_value(entry_price)
    container.wire(modules=["trade_executor", "order_calculator"])
    return container


def run_trades(container: Container):
    config = container.trade_config()
    for acc in ACCOUNTS:
        print(f"\n--- Executing on account: {acc['name']} ---")
        client = SimulatedClient(acc) if config.simulate_mode else BybitClient(acc)
        execute_trade(client)


if __name__ == "__main__":
    init_input_mode()
    if is_using_default_inputs():
        print("\n🧪 Running in DEFAULT TEST mode...\n")
    else:
        print("\n🧍 Running in MANUAL INPUT mode...\n")
    container = setup_container()
    run_trades(container)
