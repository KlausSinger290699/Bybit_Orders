from container import Container
from input_handler import choose_mode, choose_symbol, choose_order_type, get_trade_inputs
from models import TradeConfig
from trade_executor import execute_trade
from exchange_client import SimulatedClient, BybitClient
from account_config import ACCOUNTS


def collect_user_config():
    simulate_mode = choose_mode()
    symbol = choose_symbol()
    order_type = choose_order_type()
    return simulate_mode, symbol, order_type


def preview_current_price(symbol, simulate_mode):
    preview_client = SimulatedClient(ACCOUNTS[0]) if simulate_mode else BybitClient(ACCOUNTS[0])
    price = preview_client.get_market_price(symbol)
    print(f"\n📊 Current price for {symbol}: ${price}")


def setup_container() -> Container:
    simulate_mode, symbol, order_type = collect_user_config()
    preview_current_price(symbol, simulate_mode)
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
    container = setup_container()
    run_trades(container)