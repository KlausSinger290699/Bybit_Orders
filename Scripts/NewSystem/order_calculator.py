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


# ---- Pyramid planner (pure, no DI) with risk_shape switch ----
def plan_pyramid_tranches(
    *,
    balance_usdt: float,
    risk_percent: float,
    stop_price: float,
    leverage: float,
    top_price: float | None,
    bottom_price: float,
    live_price: float,
    levels: int,
    immediate_risk_pct: float,
    risk_shape: float = 1.0,  # 0 = equal risk per level (risk square → size pyramid), 1 = linear bottom-heavy risk
) -> dict:
    """
    Returns:
      {
        'side': 'long'|'short',
        'total_risk': float,
        'tranches': [{'type':'market'|'limit','price':float,'risk_usdt':float,'qty':float,'notional':float}],
        'totals': {'risk':float,'notional':float,'margin':float},
        'meta': {'risk_shape': float}
      }
    """
    if leverage <= 0:
        raise ValueError("Leverage must be greater than 0.")
    if levels < 0:
        raise ValueError("Levels must be >= 0.")
    total_risk = balance_usdt * (risk_percent / 100.0)
    if total_risk <= 0:
        raise ValueError("Total risk must be > 0.")
    if stop_price <= 0 or bottom_price <= 0 or (top_price is not None and top_price <= 0) or live_price <= 0:
        raise ValueError("Prices must be > 0.")

    s = max(0.0, min(1.0, float(risk_shape)))
    imm_pct = max(0.0, min(100.0, float(immediate_risk_pct)))

    eff_top = top_price if top_price is not None else live_price
    if bottom_price < eff_top and stop_price < bottom_price:
        side = "long"
    elif bottom_price > eff_top and stop_price > bottom_price:
        side = "short"
    else:
        raise ValueError("Invalid pyramid: expected LONG (stop < bottom < top) or SHORT (stop > bottom > top).")

    tranches: list[dict] = []

    # 🟢 Immediate tranche
    immediate_risk = imm_pct / 100.0 * total_risk
    remaining_risk = total_risk - immediate_risk

    if immediate_risk > 0:
        rpu = abs(live_price - stop_price)
        if rpu <= 0:
            raise ValueError("Live price equals stop loss; cannot size market tranche.")
        qty = immediate_risk / rpu
        tranches.append({
            "type": "market",
            "price": live_price,
            "risk_usdt": round(immediate_risk, 2),
            "qty": qty,
            "notional": qty * live_price,
        })

    if levels > 0:
        # ladder (top → bottom)
        if side == "long":
            start, end = eff_top, bottom_price
            if end >= start:
                raise ValueError("For LONG, bottom must be < top.")
            grid = [start - (start - end) * (i / levels) for i in range(1, levels + 1)]
        else:
            start, end = eff_top, bottom_price
            if end <= start:
                raise ValueError("For SHORT, bottom must be > top.")
            grid = [start + (end - start) * (i / levels) for i in range(1, levels + 1)]

        # risk sharing: blend equal vs. linear(1..L)
        if levels == 1:
            shares = [1.0]
        else:
            wsum = levels * (levels + 1) / 2  # sum 1..L
            shares = [ (1.0 - s) * (1.0 / levels) + s * (i / wsum) for i in range(1, levels + 1) ]
        scale = 1.0 / sum(shares) if shares else 1.0
        shares = [x * scale for x in shares]

        for price, share in zip(grid, shares):
            risk_i = remaining_risk * share
            rpu = abs(price - stop_price)
            if rpu <= 0:
                raise ValueError("Entry price equals stop loss; invalid level.")
            qty = risk_i / rpu
            tranches.append({
                "type": "limit",
                "price": price,
                "risk_usdt": round(risk_i, 2),
                "qty": qty,
                "notional": qty * price,
            })

    total_notional = sum(t["notional"] for t in tranches)
    total_margin = total_notional / leverage if leverage > 0 else 0.0

    return {
        "side": side,
        "total_risk": round(total_risk, 2),
        "tranches": tranches,
        "totals": {
            "risk": round(sum(t["risk_usdt"] for t in tranches), 2),
            "notional": round(total_notional, 2),
            "margin": round(total_margin, 2),
        },
        "meta": {"risk_shape": s},
    }
