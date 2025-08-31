from dependency_injector import containers, providers
from models import TradeConfig, TradeParams

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    trade_config = providers.Singleton(
        TradeConfig,
        simulate_mode=config.simulate_mode,
        symbol=config.symbol,
        order_type=config.order_type,
    )

    trade_params = providers.Singleton(
        TradeParams,
        stop_loss_price=config.stop_loss_price,
        risk_percent=config.risk_percent,
        leverage=config.leverage,
        entry_price=config.entry_price,
    )

def wire_for(config_obj: TradeConfig, params_obj: TradeParams, *, modules: list):
    c = Container()
    c.config.from_dict({
        "simulate_mode":   config_obj.simulate_mode,
        "symbol":          config_obj.symbol,
        "order_type":      config_obj.order_type,
        "stop_loss_price": params_obj.stop_loss_price,
        "risk_percent":    params_obj.risk_percent,
        "leverage":        params_obj.leverage,
        "entry_price":     params_obj.entry_price,
    })
    c.wire(modules=modules)
    return c
