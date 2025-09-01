# exchange_client.py
import ccxt
from dependency_injector.wiring import inject, Provide
from container import Container
from models import TradeConfig, TradeParams
from enums import OrderType

API_KEY         = "JVyNFG6yyMvD7zucnP"
API_SECRET      = "9dOWIBweh9EZKCnll6Pc1CSUaJ9xs9CStzSo"
API_KEYS        = []  # e.g. ["key1", "key2", ...]
API_SECRETS     = []  # e.g. ["sec1", "sec2", ...]
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
        api_keys: list[str] | None = None,
        api_secrets: list[str] | None = None,
    ):
        keys    = list(api_keys)    if api_keys    else (list(API_KEYS)    or [api_key])
        secrets = list(api_secrets) if api_secrets else (list(API_SECRETS) or [api_secret])
        if len(keys) != len(secrets):
            raise ValueError("API_KEYS and API_SECRETS must have the same length")

        self.demo_trading = bool(demo_trading)
        self.default_type = default_type
        self.clients: list[ccxt.bybit] = []
        for k, s in zip(keys, secrets):
            ex = ccxt.bybit({"apiKey": k, "secret": s, "enableRateLimit": True})
            ex.enable_demo_trading(self.demo_trading)
            ex.options["defaultType"] = self.default_type
            self.clients.append(ex)

        print(f"Loading markets ({'testnet' if self.demo_trading else 'live'})...")
        for ex in self.clients:
            ex.load_markets()
        print("Ready.\n")

        self.exchange: ccxt.bybit = self.clients[0]

    def symbol_for(self, base: str) -> str:
        return f"{base.strip().upper()}/{QUOTE}{CONTRACT_SUFFIX}"

    def get_balance_usdt(self) -> float:
        bal = self.exchange.fetch_balance()
        return float(bal["total"]["USDT"])

    def get_market_price(self, base: str) -> float:
        symbol = self.symbol_for(base)
        return float(self.exchange.fetch_ticker(symbol)["last"])

    @staticmethod
    def _position_size_for_balance(balance_usdt: float, params: TradeParams) -> float:
        entry = params.entry_price
        stop  = params.stop_loss_price
        if entry is None:
            raise ValueError("Entry price must not be None for sizing.")
        if entry == stop:
            raise ValueError("Entry and stop loss price cannot be the same.")
        if params.leverage <= 0:
            raise ValueError("Leverage must be greater than 0.")
        risk_usdt     = balance_usdt * (params.risk_percent / 100.0)
        risk_per_unit = abs(entry - stop)
        return risk_usdt / risk_per_unit

    @inject
    def apply_leverage(
        self,
        config: TradeConfig = Provide[Container.trade_config],
        params: TradeParams = Provide[Container.trade_params],
    ):
        results = []
        for ex in self.clients:
            try:
                results.append(ex.set_leverage(int(params.leverage), config.symbol))
            except Exception as e:
                results.append({"warn": str(e)})
        return results[0] if results else None

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

        primary_ex = self.clients[0]
        amt_0 = float(primary_ex.amount_to_precision(symbol, amount))
        sl_0  = primary_ex.price_to_precision(symbol, sl_px)
        primary_resp = primary_ex.create_order(
            symbol, "market", side, amt_0, None,
            {"positionIdx": 1, "stopLoss": sl_0, "slTriggerBy": "LastPrice", "tpslMode": "Full"}
        )

        if len(self.clients) > 1:
            for ex in self.clients[1:]:
                try:
                    bal = float(ex.fetch_balance()["total"]["USDT"])
                    amt_i = self._position_size_for_balance(bal, params)
                    amt_i = float(ex.amount_to_precision(symbol, amt_i))
                    sl_i  = ex.price_to_precision(symbol, sl_px)
                    ex.create_order(
                        symbol, "market", side, amt_i, None,
                        {"positionIdx": 1, "stopLoss": sl_i, "slTriggerBy": "LastPrice", "tpslMode": "Full"}
                    )
                except Exception:
                    pass

        return primary_resp

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

        primary_ex = self.clients[0]
        amt_0 = float(primary_ex.amount_to_precision(symbol, amount))
        px_0  = primary_ex.price_to_precision(symbol, float(entry))
        sl_0  = primary_ex.price_to_precision(symbol, sl_px)
        primary_resp = primary_ex.create_order(
            symbol, "limit", side, amt_0, px_0,
            {"postOnly": True, "positionIdx": 1, "stopLoss": sl_0, "slTriggerBy": "LastPrice", "tpslMode": "Full"}
        )

        if len(self.clients) > 1:
            for ex in self.clients[1:]:
                try:
                    bal = float(ex.fetch_balance()["total"]["USDT"])
                    amt_i = self._position_size_for_balance(bal, params)
                    amt_i = float(ex.amount_to_precision(symbol, amt_i))
                    px_i  = ex.price_to_precision(symbol, float(entry))
                    sl_i  = ex.price_to_precision(symbol, sl_px)
                    ex.create_order(
                        symbol, "limit", side, amt_i, px_i,
                        {"postOnly": True, "positionIdx": 1, "StopLoss": sl_i, "slTriggerBy": "LastPrice", "tpslMode": "Full"}
                    )
                except Exception:
                    pass

        return primary_resp
