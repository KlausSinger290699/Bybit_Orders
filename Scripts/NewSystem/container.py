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
