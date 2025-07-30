from order_calculator import calculate_position_sizing

def execute_trade(client, symbol, stop_loss_price, risk_percent, leverage):
    entry_price = client.get_market_price(symbol)
    balance = client.get_balance_usdt()

    result = calculate_position_sizing(entry_price, stop_loss_price, balance, risk_percent, leverage)

    if not result["is_leverage_safe"]:
        print(f"\n❌ ERROR: Leverage too high! Margin (${result['margin_required']}) "
              f"doesn't support your stop loss (${result['risk_usdt']}).")
        print(f"🛡️  Max safe leverage = {result['max_safe_leverage']}x")
        return

    client.set_leverage(symbol, leverage)
    side = "buy" if result["direction"] == "long" else "sell"

    print(f"\n{result['direction'].upper()} {result['position_size']} BTC @ ${entry_price} (SL: ${stop_loss_price})")
    print(f"Max loss: ${result['risk_usdt']} | Margin used: ${result['margin_required']} | "
          f"Leverage: {result['leverage']}x")

    confirm = input("Confirm order? (y/n): ").strip().lower()
    if confirm != "y":
        print("❌ Order cancelled.")
        return

    client.place_market_order(symbol, side, result["position_size"])
    client.place_stop_loss(symbol, side, stop_loss_price, result["position_size"])
    print("✅ Trade executed.")
