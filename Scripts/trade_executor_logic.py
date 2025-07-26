from account_config import ACCOUNTS
from exchange_client import create_client, get_balance_usdt, get_price, place_market_order
from order_calculator import calculate_position_size

def execute_trade_for_account(config, risk_percent, leverage, symbol, side):
    client = create_client(config)
    balance = get_balance_usdt(client)
    price = get_price(client, symbol)
    amount = calculate_position_size(balance, risk_percent, leverage, price)

    print(f"[{config['name']}] Balance: ${balance:.2f}, Price: {price:.2f}, Amount: {amount} BTC")

    confirm = input(f"Place {side.upper()} order on {config['name']}? (y/n): ").strip().lower()
    if confirm == 'y':
        order = place_market_order(client, symbol, side, amount)
        print(f"Order placed: {order['id']}")
    else:
        print("Skipped.")

def run_trading():
    symbol = "BTC/USDT"
    side = "buy"
    try:
        risk_percent = float(input("Enter risk % (e.g., 1.5): "))
        leverage = float(input("Enter leverage (e.g., 10): "))
    except ValueError:
        print("Invalid input.")
        return

    for config in ACCOUNTS:
        execute_trade_for_account(config, risk_percent, leverage, symbol, side)
