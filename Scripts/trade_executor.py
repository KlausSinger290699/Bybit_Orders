from order_calculator import calculate_position_sizing

def execute_trade(client, entry_price, stop_loss_price, risk_percent, leverage, symbol):
    balance = client.get_balance_usdt()
    result = calculate_position_sizing(entry_price, stop_loss_price, balance, risk_percent, leverage)

    if not result["is_leverage_safe"]:
        print(f"\n❌ ERROR: Leverage too high! Margin (${result['margin_required']}) "
              f"doesn't support your stop loss (${result['risk_usdt']}).")
        print(f"🛡️  Max safe leverage = {result['max_safe_leverage']}x")
        return

    client.set_leverage(symbol, leverage)
    size = result["position_size"]
    side = "buy" if result["direction"] == "long" else "sell"

    print(f"\n[{client.__class__.__name__}] Balance: ${balance:.2f}, "
          f"{result['direction'].upper()} {size} BTC @ ${entry_price} (SL: ${stop_loss_price}) "
          f"Risk: ${result['risk_usdt']} | Margin: ${result['margin_required']}")

    confirm = input("Execute order? (y/n): ").strip().lower()
    if confirm == 'y':
        order = client.place_market_order(symbol, side, size)
        print(f"✅ Order placed: {order['id']}")
    else:
        print("❌ Skipped.")
