from exchange_client import SimulatedClient, BybitClient
from trade_executor import execute_trade
from account_config import ACCOUNTS
from input_handler import choose_mode, choose_symbol, choose_order_type, get_trade_inputs
from models import TradeConfig, TradeParams

def build_client(config, simulate_mode):
    return SimulatedClient(config) if simulate_mode else BybitClient(config)

def preview_price(client, symbol):
    price = client.get_market_price(symbol)
    print(f"\n📊 Current price for {symbol}: ${price}\n")
    return price

def run_trades(config: TradeConfig, params: TradeParams):
    for acc in ACCOUNTS:
        print(f"\n--- Executing on account: {acc['name']} ---")
        client = build_client(acc, config.simulate_mode)
        execute_trade(client, config, params)


if __name__ == "__main__":
    simulate_mode = choose_mode()
    symbol = choose_symbol()
    order_type = choose_order_type()

    config = TradeConfig(simulate_mode=simulate_mode, symbol=symbol, order_type=order_type)

    preview_client = build_client(ACCOUNTS[0], config.simulate_mode)
    preview_price(preview_client, config.symbol)

    stop_loss_price, risk_percent, leverage, entry_price = get_trade_inputs(config.order_type)
    params = TradeParams(
        stop_loss_price=stop_loss_price,
        risk_percent=risk_percent,
        leverage=leverage,
        entry_price=entry_price
    )

    run_trades(config, params)