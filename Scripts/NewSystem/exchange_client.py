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

    def get_current_leverage(self, symbol: str) -> float | None:
        try:
            try:
                positions = self.exchange.fetch_positions([symbol])
            except Exception:
                positions = self.exchange.fetch_positions()
            if isinstance(positions, list):
                for p in positions:
                    if p.get("symbol") == symbol:
                        lev = p.get("leverage") or (p.get("info", {}) or {}).get("leverage")
                        return float(lev) if lev else None
            elif isinstance(positions, dict):
                lev = positions.get("leverage") or (positions.get("info", {}) or {}).get("leverage")
                return float(lev) if lev else None
        except Exception:
            pass
        return None

    @inject
    def apply_leverage(
        self,
        config: TradeConfig = Provide[Container.trade_config],
        params: TradeParams = Provide[Container.trade_params],
    ):
        desired = params.leverage
        if desired is None or desired == "" or float(desired) <= 0:
            return {"skipped": "no leverage requested"}
        desired_int = int(float(desired))

        current = self.get_current_leverage(config.symbol)
        if current is not None and int(float(current)) == desired_int:
            return {"skipped": "leverage already set"}

        try:
            return self.exchange.set_leverage(desired_int, config.symbol)
        except ccxt.BadRequest as e:
            msg = str(e)
            if "110043" in msg or "leverage not modified" in msg.lower():
                return {"ignored": "leverage not modified"}
            raise

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
