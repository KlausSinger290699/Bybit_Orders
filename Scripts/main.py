from dependency_injector.wiring import inject, Provide
from container import Container
from input_handler import choose_mode, choose_symbol, choose_order_type, get_trade_inputs
from models import TradeConfig, TradeParams
from trade_executor import execute_trade
from exchange_client import SimulatedClient, BybitClient
from account_config import ACCOUNTS


def build_client(config, simulate_mode):
    return SimulatedClient(config) if simulate_mode else BybitClient(config)


def preview_price(client, symbol):
    price = client.get_market_price(symbol)
    print(f"\n📊 Current price for {symbol}: ${price}")
    return price


def run_trades(container: Container):
    config = container.trade_config()
    for acc in ACCOUNTS:
        print(f"\n--- Executing on account: {acc['name']} ---")
        client = SimulatedClient(acc) if config.simulate_mode else BybitClient(acc)
        execute_trade(client)


if __name__ == "__main__":
    container = Container()
    container.wire(modules=["trade_executor", "order_calculator"])

    simulate_mode = choose_mode()
    symbol = choose_symbol()
    order_type = choose_order_type()

    config = TradeConfig(simulate_mode=simulate_mode, symbol=symbol, order_type=order_type)
    container.config.simulate_mode.from_value(config.simulate_mode)
    container.config.symbol.from_value(config.symbol)
    container.config.order_type.from_value(config.order_type)

    preview_client = build_client(ACCOUNTS[0], simulate_mode)
    preview_price(preview_client, symbol)

    stop_loss_price, risk_percent, leverage, entry_price = get_trade_inputs(order_type)
    container.config.stop_loss_price.from_value(stop_loss_price)
    container.config.risk_percent.from_value(risk_percent)
    container.config.leverage.from_value(leverage)
    container.config.entry_price.from_value(entry_price)

    run_trades(container)
