from order_calculator import calculate_position_sizing
from enums import OrderType

def execute_trade(client, symbol, stop_loss_price, risk_percent, leverage, order_type, entry_price=None):
    market_price = client.get_market_price(symbol)
    effective_entry = entry_price if order_type == OrderType.LIMIT else market_price

    balance = client.get_balance_usdt()

    result = calculate_position_sizing(
        entry_price=effective_entry,
        stop_loss_price=stop_loss_price,
        balance_usdt=balance,
        risk_percent=risk_percent,
        leverage=leverage
    )

    if not result["is_leverage_safe"]:
        print(f"\n❌ ERROR: Leverage too high! Margin (${result['margin_required']}) "
              f"doesn't support your stop loss (${result['risk_usdt']}).")
        print(f"🛡️  Max safe leverage = {result['max_safe_leverage']}x")
        return

    client.set_leverage(symbol, leverage)
    side = "buy" if result["direction"] == "long" else "sell"

    print(f"{result['direction'].upper()} {result['position_size']} {symbol} @ ${effective_entry} (SL: ${stop_loss_price})")
    print(f"Max loss: ${result['risk_usdt']} | Margin used: ${result['margin_required']} | "
          f"Leverage: {result['leverage']}x")

    if order_type == OrderType.MARKET:
        client.place_market_order(symbol, side, result["position_size"])
    elif order_type == OrderType.LIMIT:
        client.place_limit_order(symbol, side, entry_price, result["position_size"])

    client.place_stop_loss(symbol, side, stop_loss_price, result["position_size"])
    print("✅ Trade executed.")


    # confirm = input("Confirm order? (y/n): ").strip().lower()
    # if confirm != "y":
    #     print("❌ Order cancelled.")
    #     return