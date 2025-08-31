import ccxt
from dependency_injector.wiring import inject, Provide
from container import Container
from models import TradeConfig, TradeParams
from enums import OrderType

API_KEY         = "JVyNFG6yyMvD7zucnP"
API_SECRET      = "9dOWIBweh9EZKCnll6Pc1CSUaJ9xs9CStzSo"
DEMO_TRADING    = True
DEFAULT_TYPE    = "future"
QUOTE           = "USDT"
CONTRACT_SUFFIX = ":USDT"

class ExchangeClient:
    def __init__(
        self,
        api_key: str = API_KEY,
        api_secret: str = API_SECRET,
        demo_trading: bool = DEMO_TRADING,
        default_type: str = DEFAULT_TYPE,
    ):
        self.exchange = ccxt.bybit({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
        })
        self.exchange.enable_demo_trading(bool(demo_trading))
        self.exchange.options["defaultType"] = default_type
        print(f"Loading markets ({'testnet' if demo_trading else 'live'})...")
        self.exchange.load_markets()
        print("Ready.\n")

    def symbol_for(self, base: str) -> str:
        return f"{base.strip().upper()}/{QUOTE}{CONTRACT_SUFFIX}"

    def get_balance_usdt(self) -> float:
        bal = self.exchange.fetch_balance()
        return float(bal["total"]["USDT"])

    def get_market_price(self, base: str) -> float:
        symbol = self.symbol_for(base)
        return float(self.exchange.fetch_ticker(symbol)["last"])

    @inject
    def apply_leverage(
        self,
        config: TradeConfig = Provide[Container.trade_config],
        params: TradeParams = Provide[Container.trade_params],
    ):
        return self.exchange.set_leverage(int(params.leverage), config.symbol)

    @inject
    def market_order_with_stop(
        self,
        side: str,
        amount: float,
        config: TradeConfig = Provide[Container.trade_config],
        params: TradeParams = Provide[Container.trade_params],
    ):
        symbol = config.symbol
        sl_px  = params.stop_loss_price
        amt = float(self.exchange.amount_to_precision(symbol, amount))
        sl  = self.exchange.price_to_precision(symbol, sl_px)
        return self.exchange.create_order(
            symbol, "market", side, amt, None,
            {"positionIdx": 1, "stopLoss": sl, "slTriggerBy": "LastPrice", "tpslMode": "Full"}
        )

    @inject
    def limit_order_with_stop(
        self,
        side: str,
        amount: float,
        config: TradeConfig = Provide[Container.trade_config],
        params: TradeParams = Provide[Container.trade_params],
    ):
        symbol = config.symbol
        entry  = params.entry_price
        sl_px  = params.stop_loss_price
        if entry is None:
            raise ValueError("entry_price must be provided for LIMIT orders.")
        amt = float(self.exchange.amount_to_precision(symbol, amount))
        px  = self.exchange.price_to_precision(symbol, float(entry))
        sl  = self.exchange.price_to_precision(symbol, sl_px)
        return self.exchange.create_order(
            symbol, "limit", side, amt, px,
            {"postOnly": True, "positionIdx": 1, "stopLoss": sl, "slTriggerBy": "LastPrice", "tpslMode": "Full"}
        )
