import os
import ccxt

class ExchangeClient:
    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        testnet: bool = True,
        default_type: str = "future",
    ):
        api_key    = api_key or os.getenv("BYBIT_API_KEY", "")
        api_secret = api_secret or os.getenv("BYBIT_API_SECRET", "")

        self.exchange = ccxt.bybit({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
        })
        # Testnet/demo
        try:
            self.exchange.enable_demo_trading(testnet)
        except Exception:
            pass  # older ccxt versions may not have this; ignore if unnecessary
        self.exchange.options["defaultType"] = default_type
        self.exchange.load_markets()

    # ---------- helpers ----------
    def get_balance_usdt(self) -> float:
        bal = self.exchange.fetch_balance()
        total = bal.get("total", {})
        return float(total.get("USDT", 0.0))

    def get_market_price(self, symbol: str) -> float:
        return float(self.exchange.fetch_ticker(symbol)["last"])

    def set_leverage(self, leverage: float, symbol: str):
        try:
            return self.exchange.set_leverage(int(leverage), symbol)
        except Exception as e:
            # Non-fatal; many times leverage stays same
            return {"error": str(e)}

    # ---------- orders ----------
    def market_order_with_sl(self, symbol: str, side: str, amount: float, stop_loss_price: float):
        amount = float(self.exchange.amount_to_precision(symbol, amount))
        sl     = self.exchange.price_to_precision(symbol, stop_loss_price)
        return self.exchange.create_order(
            symbol, "market", side, amount, None,
            {"positionIdx": 1, "stopLoss": sl, "slTriggerBy": "LastPrice", "tpslMode": "Full"}
        )

    def limit_order_with_sl(self, symbol: str, side: str, amount: float, entry_price: float, stop_loss_price: float, post_only: bool = True):
        amount = float(self.exchange.amount_to_precision(symbol, amount))
        price  = self.exchange.price_to_precision(symbol, entry_price)
        sl     = self.exchange.price_to_precision(symbol, stop_loss_price)
        return self.exchange.create_order(
            symbol, "limit", side, amount, price,
            {"postOnly": post_only, "positionIdx": 1, "stopLoss": sl, "slTriggerBy": "LastPrice", "tpslMode": "Full"}
        )
