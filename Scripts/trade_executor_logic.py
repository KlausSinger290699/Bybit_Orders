from account_config import ACCOUNTS
from exchange_client import create_client, get_balance_usdt, place_market_order, set_leverage
from order_calculator import calculate_position_sizing

def execute_trade_for_account(config, entry_price, stop_loss_price, risk_percent, leverage, symbol):
    client = create_client(config)
    balance = get_balance_usdt(client)

    result = calculate_position_sizing(entry_price, stop_loss_price, balance, risk_percent, leverage)

    if not result["is_leverage_safe"]:
        print(f"\n❌ ERROR: Leverage too high! Margin (${result['margin_required']}) "
              f"doesn't support your stop loss (${result['risk_usdt']}).")
        print(f"🛡️  Max safe leverage = {result['max_safe_leverage']}x")
        return

    set_leverage(client, symbol, leverage)

    size = result["position_size"]
    side = "buy" if result["direction"] == "long" else "sell"

    print(f"[{config['name']}] Balance: ${balance:.2f}, "
          f"{result['direction'].upper()} {size} BTC/USDT @ {entry_price} (SL: {stop_loss_price}) "
          f"Risk: ${result['risk_usdt']}")

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
        leverage = float(input("Enter leverage: "))
    except ValueError:
        print("Invalid input.")
        return

    for config in ACCOUNTS:
        execute_trade_for_account(config, entry, stop, risk_percent, leverage, symbol)
