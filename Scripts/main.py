from exchange_client import SimulatedClient, BybitClient
from trade_executor import execute_trade
from account_config import ACCOUNTS
from input_handler import choose_mode, choose_symbol, choose_order_type, get_trade_inputs

def build_client(config, simulate_mode):
    return SimulatedClient(config) if simulate_mode else BybitClient(config)

def preview_price(client, symbol):
    price = client.get_market_price(symbol)
    print(f"\n📊 Current price for {symbol}: ${price}\n")
    return price

def run_trades(simulate_mode, symbol, stop_loss_price, risk_percent, leverage, order_type, entry_price):
    for config in ACCOUNTS:
        print(f"\n--- Executing on account: {config['name']} ---")
        client = build_client(config, simulate_mode)
        execute_trade(client, symbol, stop_loss_price, risk_percent, leverage, order_type, entry_price)


if __name__ == "__main__":
    simulate_mode = choose_mode()
    symbol = choose_symbol()
    order_type = choose_order_type()

    preview_client = build_client(ACCOUNTS[0], simulate_mode)
    preview_price(preview_client, symbol)

    stop_loss_price, risk_percent, leverage, entry_price = get_trade_inputs(order_type)
    run_trades(simulate_mode, symbol, stop_loss_price, risk_percent, leverage, order_type, entry_price)
