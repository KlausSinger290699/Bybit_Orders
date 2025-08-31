import ccxt
from enums import OrderType

# ===== CONFIG (as requested: inline, not hidden) =====
API_KEY        = "JVyNFG6yyMvD7zucnP"
API_SECRET     = "9dOWIBweh9EZKCnll6Pc1CSUaJ9xs9CStzSo"
DEMO_TRADING   = True
DEFAULT_TYPE   = "future"
QUOTE          = "USDT"
CONTRACT_SUFFIX= ":USDT"

class ExchangeClient:
    """
    Only this client knows API keys, demo/live, Bybit symbol formatting,
    precision, balances, prices, leverage, and order placement.
    """

    def __init__(
        self,
        api_key: str = API_KEY,
        api_secret: str = API_SECRET,
        demo_trading: bool = DEMO_TRADING,
        default_type: str = DEFAULT_TYPE,
    ):
        self.demo_trading = demo_trading

        self.exchange = ccxt.bybit({
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
        })

        # Demo (testnet) vs live
        try:
            self.exchange.enable_demo_trading(demo_trading)
        except Exception:
            pass

        self.exchange.options["defaultType"] = default_type
        self.exchange.load_markets()

    # ---------- symbol & formatting ----------
    def symbol_for(self, base: str) -> str:
        """User types 'rune' -> 'RUNE/USDT:USDT'"""
        base_clean = base.strip().upper()
        return f"{base_clean}/{QUOTE}{CONTRACT_SUFFIX}"

    # ---------- data helpers ----------
    def get_balance_usdt(self) -> float:
        bal = self.exchange.fetch_balance()
        # keep identical to your standalone example style:
        return float(bal["total"]["USDT"])

    def get_market_price(self, base: str) -> float:
        symbol = self.symbol_for(base)
        return float(self.exchange.fetch_ticker(symbol)["last"])

    def set_leverage(self, leverage: float, base: str):
        symbol = self.symbol_for(base)
        try:
            return self.exchange.set_leverage(int(leverage), symbol)
        except Exception as e:
            return {"warn": str(e)}

    # ---------- order placement (with SL via TP/SL section) ----------
    def place_order_with_stop(
        self,
        order_type: OrderType,
        side: str,               # "buy" or "sell"
        base: str,               # e.g., "RUNE"
        amount: float,           # base units from sizing
        stop_loss_price: float,
        entry_price: float | None = None,  # required for LIMIT
        post_only: bool = True,
    ):
        symbol = self.symbol_for(base)
        amt    = float(self.exchange.amount_to_precision(symbol, amount))
        sl_px  = self.exchange.price_to_precision(symbol, stop_loss_price)

        if order_type == OrderType.MARKET:
            return self.exchange.create_order(
                symbol, "market", side, amt, None,
                {"positionIdx": 1, "stopLoss": sl_px, "slTriggerBy": "LastPrice", "tpslMode": "Full"}
            )

        if entry_price is None:
            raise ValueError("entry_price must be provided for LIMIT orders.")
        px = self.exchange.price_to_precision(symbol, entry_price)
        return self.exchange.create_order(
            symbol, "limit", side, amt, px,
            {"postOnly": post_only, "positionIdx": 1, "stopLoss": sl_px, "slTriggerBy": "LastPrice", "tpslMode": "Full"}
        )
