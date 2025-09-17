from dependency_injector.wiring import inject, Provide
from order_calculator import calculate_position_sizing
from container import Container
from enums import OrderType
from models import TradeConfig, TradeParams

@inject
def execute_trade(
    client,
    config: TradeConfig = Provide[Container.trade_config],
    params: TradeParams = Provide[Container.trade_params],
):
    if config.order_type == OrderType.MARKET:
        params.entry_price = client.get_market_price(config.symbol)

    if params.entry_price is None:
        raise ValueError("Entry price must not be None.")

    balance = client.get_balance_usdt()
    result = calculate_position_sizing(balance)

    if not result["is_leverage_safe"]:
        print(f"\n❌ ERROR: Leverage too high! Margin (${result['margin_required']}) "
              f"doesn't support your stop loss (${result['risk_usdt']}).")
        print(f"🛡️  Max safe leverage = {result['max_safe_leverage']}x")
        return

    client.set_leverage(config.symbol, params.leverage)
    side = "buy" if result["direction"] == "long" else "sell"

    print(f"📈 {result['direction'].upper()} {result['position_size']} {config.symbol} @ ${params.entry_price} (SL: ${params.stop_loss_price})")
    print(f"💰 Balance     : ${balance:,.2f}")
    print(f"🔻 Max loss    : ${result['risk_usdt']:,.2f}")
    print(f"🧮 Margin used : ${result['margin_required']:,.2f}")
    print(f"⚙️  Leverage    : {result['leverage']}x")

    if config.order_type == OrderType.MARKET:
        client.place_market_order(config.symbol, side, result["position_size"])
    else:
        client.place_limit_order(config.symbol, side, params.entry_price, result["position_size"])

    client.place_stop_loss(config.symbol, side, params.stop_loss_price, result["position_size"])
    print("✅ Trade executed.")
