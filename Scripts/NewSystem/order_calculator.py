# order_calculator.py
from dependency_injector.wiring import inject, Provide
from container import Container
from models import TradeConfig, TradeParams

@inject
def calculate_position_sizing(
    balance_usdt: float,
    config: TradeConfig = Provide[Container.trade_config],
    params: TradeParams = Provide[Container.trade_params],
):
    entry_price     = params.entry_price
    stop_loss_price = params.stop_loss_price
    leverage        = params.leverage
    risk_percent    = params.risk_percent

    if entry_price is None:
        raise ValueError("Entry price must not be None.")
    if entry_price == stop_loss_price:
        raise ValueError("Entry and stop loss price cannot be the same.")
    if leverage <= 0:
        raise ValueError("Leverage must be greater than 0.")

    direction       = "long" if stop_loss_price < entry_price else "short"
    risk_usdt       = balance_usdt * (risk_percent / 100)
    risk_per_unit   = abs(entry_price - stop_loss_price)
    position_size   = risk_usdt / risk_per_unit
    notional_value  = position_size * entry_price
    margin_required = notional_value / leverage
    max_safe_lev    = notional_value / risk_usdt
    is_lev_safe     = leverage <= max_safe_lev

    return {
        "direction": direction,
        "position_size": round(position_size, 6),
        "risk_usdt": round(risk_usdt, 2),
        "notional_value": round(notional_value, 2),
        "margin_required": round(margin_required, 2),
        "leverage": leverage,
        "max_safe_leverage": round(max_safe_lev, 2),
        "is_leverage_safe": is_lev_safe
    }
