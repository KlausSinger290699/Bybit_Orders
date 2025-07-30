from exchange_client import SimulatedClient, BybitClient
from trade_executor import execute_trade
from account_config import ACCOUNTS
from input_handler import choose_mode, choose_symbol, get_trade_inputs

def build_client(config, simulate_mode):
    return SimulatedClient(config) if simulate_mode else BybitClient(config)

def preview_price(client, symbol):
    price = client.get_market_price(symbol)
    print(f"\n📊 Current price for {symbol}: ${price}\n")
    return price

def run_trades(simulate_mode, symbol, stop_loss_price, risk_percent, leverage):
    for config in ACCOUNTS:
        print(f"\n--- Executing on account: {config['name']} ---")
        client = build_client(config, simulate_mode)
        execute_trade(client, symbol, stop_loss_price, risk_percent, leverage)

if __name__ == "__main__":
    simulate_mode = choose_mode()
    symbol = choose_symbol()

    preview_client = build_client(ACCOUNTS[0], simulate_mode)
    preview_price(preview_client, symbol)

    stop_loss_price, risk_percent, leverage = get_trade_inputs()
    run_trades(simulate_mode, symbol, stop_loss_price, risk_percent, leverage)
