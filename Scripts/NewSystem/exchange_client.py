# exchange_client.py
import ccxt
from enums import OrderType
from models import OrderPlan

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

    def apply_leverage(self, plan: OrderPlan):
        try:
            return self.exchange.set_leverage(int(plan.leverage), plan.symbol)
        except Exception as e:
            return {"warn": str(e)}

    def place_order_with_stop(self, plan: OrderPlan):
        symbol = plan.symbol
        amt    = float(self.exchange.amount_to_precision(symbol, plan.amount))
        sl_px  = self.exchange.price_to_precision(symbol, plan.stop_loss_price)

        if plan.order_type == OrderType.MARKET:
            return self.exchange.create_order(
                symbol, "market", plan.side, amt, None,
                {"positionIdx": 1, "stopLoss": sl_px, "slTriggerBy": "LastPrice", "tpslMode": "Full"}
            )

        if plan.entry_price is None:
            raise ValueError("entry_price must be provided for LIMIT orders.")
        px = self.exchange.price_to_precision(symbol, float(plan.entry_price))
        return self.exchange.create_order(
            symbol, "limit", plan.side, amt, px,
            {"postOnly": True, "positionIdx": 1, "stopLoss": sl_px, "slTriggerBy": "LastPrice", "tpslMode": "Full"}
        )
