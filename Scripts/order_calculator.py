def calculate_position_sizing(entry_price, stop_loss_price, balance_usdt, risk_percent, leverage):
    if entry_price == stop_loss_price:
        raise ValueError("Entry and stop loss price cannot be the same.")
    if leverage <= 0:
        raise ValueError("Leverage must be greater than 0.")

    direction = "long" if stop_loss_price < entry_price else "short"
    risk_usdt = balance_usdt * (risk_percent / 100)
    risk_per_unit = abs(entry_price - stop_loss_price)
    position_size = risk_usdt / risk_per_unit
    notional_value = position_size * entry_price
    margin_required = notional_value / leverage
    max_safe_leverage = notional_value / risk_usdt
    is_leverage_safe = leverage <= max_safe_leverage

    return {
        "direction": direction,
        "position_size": round(position_size, 6),
        "risk_usdt": round(risk_usdt, 2),
        "notional_value": round(notional_value, 2),
        "margin_required": round(margin_required, 2),
        "leverage": leverage,
        "max_safe_leverage": round(max_safe_leverage, 2),
        "is_leverage_safe": is_leverage_safe
    }
