from order_calculator import calculate_position_size

def simulate_order(balance, risk_percent, leverage, entry_price, symbol="BTC/USDT", side="buy"):
    amount = calculate_position_size(balance, risk_percent, leverage, entry_price)
    cost = amount * entry_price
    print(f"[SIMULATION] {side.upper()} {amount} {symbol} @ {entry_price} = ${cost:.2f} (Leverage: {leverage}x, Risk: {risk_percent}%)")

def run_simulation():
    try:
        balance = float(input("Enter USDT balance: "))
        entry_price = float(input("Enter entry price: "))
        risk_percent = float(input("Enter risk %: "))
        leverage = float(input("Enter leverage: "))
    except ValueError:
        print("Invalid input.")
        return

    simulate_order(balance, risk_percent, leverage, entry_price)
