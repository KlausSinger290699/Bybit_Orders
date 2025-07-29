from order_calculator import calculate_position_sizing

def run_simulation():
    try:
        balance = float(input("Enter USDT balance: "))
        entry = float(input("Enter entry price: "))
        stop = float(input("Enter stop loss price: "))
        risk_percent = float(input("Enter risk %: "))
        leverage = float(input("Enter leverage: "))
    except ValueError:
        print("Invalid input.")
        return

    try:
        result = calculate_position_sizing(entry, stop, balance, risk_percent, leverage)
    except ValueError as e:
        print(f"Error: {e}")
        return

    if not result["is_leverage_safe"]:
        print(f"\n❌ ERROR: Leverage too high! Margin (${result['margin_required']}) "
              f"doesn't support your stop loss (${result['risk_usdt']}).")
        print(f"🛡️  Max safe leverage = {result['max_safe_leverage']}x")
        return

    print(f"[SIMULATION] {result['direction'].upper()} {result['position_size']} BTC @ ${entry} (SL: ${stop})")
    print(f"Max loss: ${result['risk_usdt']} | Margin used: ${result['margin_required']} | "
          f"Notional: ${result['notional_value']} | Leverage: {result['leverage']}x")
