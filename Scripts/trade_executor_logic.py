from account_config import ACCOUNTS
from exchange_client import create_client, get_balance_usdt, place_market_order
from order_calculator import calculate_position_sizing

def execute_trade_for_account(config, risk_percent, entry_price, stop_loss_price, symbol):
    client = create_client(config)
    balance = get_balance_usdt(client)

    result = calculate_position_sizing(entry_price, stop_loss_price, balance, risk_percent)
    size = result["position_size"]
    side = "buy" if result["direction"] == "long" else "sell"

    print(f"[{config['name']}] Balance: ${balance:.2f}, "
          f"{result['direction'].upper()} {size} BTC/USDT @ {entry_price} (SL: {stop_loss_price}) "
          f"Risk: ${result['risk_amount']}")

    confirm = input(f"Place {side.upper()} order on {config['name']}? (y/n): ").strip().lower()
    if confirm == 'y':
        order = place_market_order(client, symbol, side, size)
        print(f"Order placed: {order['id']}")
    else:
        print("Skipped.")

def run_trading():
    symbol = "BTC/USDT"
    try:
        entry = float(input("Enter entry price: "))
        stop = float(input("Enter stop loss price: "))
        risk_percent = float(input("Enter risk %: "))
    except ValueError:
        print("Invalid input.")
        return

    for config in ACCOUNTS:
        execute_trade_for_account(config, risk_percent, entry, stop, symbol)
