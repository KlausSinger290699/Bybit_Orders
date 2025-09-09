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


# ---- NEW: Pyramid planner (pure function, no DI) ----
def plan_pyramid_tranches(
    *,
    balance_usdt: float,
    risk_percent: float,
    stop_price: float,
    leverage: float,
    top_price: float | None,     # None → use live price as "top"
    bottom_price: float,
    live_price: float,
    levels: int,                 # number of limit levels (excludes immediate market tranche)
    immediate_risk_pct: float,   # 0..100 of total risk, done as market at live_price
) -> dict:
    """
    Returns a plan dict with:
      {
        'side': 'long'|'short',
        'total_risk': float,
        'tranches': [
           {'type':'market'|'limit','price':float,'risk_usdt':float,'qty':float,'notional':float}
        ],
        'totals': {'risk':float,'notional':float,'margin':float}
      }
    Rules:
      - Heavier risk near the bottom (better R:R): linear weights 1..levels (bottom has max weight).
      - Market tranche is optional and uses live_price, consuming immediate_risk_pct of total risk.
      - For LONG: stop < bottom < top; For SHORT: stop > bottom > top. Raises ValueError otherwise.
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

    # Determine side and sanitize top
    eff_top = top_price if top_price is not None else live_price
    if bottom_price < eff_top and stop_price < bottom_price:
        side = "long"
    elif bottom_price > eff_top and stop_price > bottom_price:
        side = "short"
    else:
        raise ValueError("Invalid pyramid: expected LONG (stop < bottom < top) or SHORT (stop > bottom > top).")

    # Market (immediate) tranche
    tranches: list[dict] = []
    immediate_risk = max(0.0, min(100.0, immediate_risk_pct)) / 100.0 * total_risk
    remaining_risk = total_risk - immediate_risk

    if immediate_risk > 0:
        risk_per_unit = abs(live_price - stop_price)
        if risk_per_unit <= 0:
            raise ValueError("Live price equals stop loss; cannot size market tranche.")
        qty = immediate_risk / risk_per_unit
        tranches.append({
            "type": "market",
            "price": live_price,
            "risk_usdt": round(immediate_risk, 2),
            "qty": qty,
            "notional": qty * live_price,
        })

    # Grid prices from top -> bottom for limit orders
    if levels > 0:
        # Prices descending for long, ascending for short
        if side == "long":
            start = eff_top
            end = bottom_price
            if end >= start:
                raise ValueError("For LONG, bottom must be < top.")
            grid = [start - (start - end) * (i / levels) for i in range(1, levels + 1)]
        else:
            start = eff_top
            end = bottom_price
            if end <= start:
                raise ValueError("For SHORT, bottom must be > top.")
            grid = [start + (end - start) * (i / levels) for i in range(1, levels + 1)]

        # Linear weights 1..levels (bottom = largest weight)
        weights = [i for i in range(1, levels + 1)]
        wsum = float(sum(weights))
        for price, w in zip(grid, weights):
            risk_i = remaining_risk * (w / wsum)
            risk_per_unit = abs(price - stop_price)
            if risk_per_unit <= 0:
                raise ValueError("Entry price equals stop loss; invalid level.")
            qty = risk_i / risk_per_unit
            tranches.append({
                "type": "limit",
                "price": price,
                "risk_usdt": round(risk_i, 2),
                "qty": qty,
                "notional": qty * price,
            })

    # Totals
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
    }
