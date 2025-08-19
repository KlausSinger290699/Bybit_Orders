import ccxt
import random

class ExchangeClient:
    def get_balance_usdt(self): raise NotImplementedError
    def get_market_price(self, symbol): raise NotImplementedError
    def set_leverage(self, symbol, leverage): raise NotImplementedError
    def place_market_order(self, symbol, side, amount): raise NotImplementedError
    def place_limit_order(self, symbol, side, price, amount): raise NotImplementedError
    def place_stop_loss(self, symbol, side, stop_price, amount): raise NotImplementedError

class BybitClient(ExchangeClient):
    def __init__(self, config):
        self.client = ccxt.bybit({
            "apiKey": config["apiKey"],
            "secret": config["secret"],
            "enableRateLimit": True,
        })

        if config.get("sandbox"):
            if hasattr(self.client, "enable_demo_trading"):
                self.client.enable_demo_trading(True)
            else:
                self.client.set_sandbox_mode(True)
                if "test" in self.client.urls:
                    self.client.urls["api"] = self.client.urls["test"]

        self.client.options["defaultType"] = "future"
        self.client.load_markets()

    def get_balance_usdt(self):
        bal = self.client.fetch_balance()
        if "total" in bal and isinstance(bal["total"], dict):
            return bal["total"].get("USDT", 0)
        if "USDT" in bal and isinstance(bal["USDT"], dict):
            return bal["USDT"].get("total", 0)
        return 0

    def get_market_price(self, symbol):
        return self.client.fetch_ticker(symbol)["last"]

    def set_leverage(self, symbol, leverage):
        try:
            return self.client.set_leverage(leverage, symbol)
        except Exception:
            m = self.client.market(symbol)
            try:
                return self.client.privatePostV5PositionSetLeverage({
                    "category": "linear",
                    "symbol": m["id"],
                    "buyLeverage": str(leverage),
                    "sellLeverage": str(leverage),
                })
            except Exception:
                return self.client.privateLinearPostPositionSetLeverage({
                    "symbol": m["id"],
                    "buy_leverage": leverage,
                    "sell_leverage": leverage,
                })

    def place_market_order(self, symbol, side, amount):
        return self.client.create_order(symbol=symbol, type="market", side=side, amount=amount)

    def place_limit_order(self, symbol, side, price, amount):
        try:
            return self.client.create_order(symbol, "limit", side, amount, price, {"postOnly": True})
        except Exception:
            return self.client.create_order(symbol, "limit", side, amount, price, {"timeInForce": "PostOnly"})

    def place_stop_loss(self, symbol, side, stop_price, amount):
        opposite = "sell" if side == "buy" else "buy"
        try:
            return self.client.create_order(symbol, "market", opposite, amount, None,
                                            {"reduceOnly": True, "triggerPrice": stop_price})
        except Exception:
            return self.client.create_order(symbol, "market", opposite, amount, None,
                                            {"reduceOnly": True, "stopPrice": stop_price})

SIM_BALANCE_MAP = {
    ("your_testnet_key", "your_testnet_secret"): 100000,
    ("your_real_key", "your_real_secret"): 200000
}
DEFAULT_BALANCE = 100000

SIM_PRICES = {
    "BTC/USDT": 120000,
    "ETH/USDT": 3000,
    "SOL/USDT": 150,
    "XRP/USDT": 0.6,
    "DOGE/USDT": 0.1
}
DEFAULT_SIM_PRICE = 100000

class SimulatedClient(ExchangeClient):
    def __init__(self, config):
        key_pair = (config["apiKey"], config["secret"])
        self._fake_balance = SIM_BALANCE_MAP.get(key_pair, DEFAULT_BALANCE)

    def get_balance_usdt(self):
        return self._fake_balance

    def get_market_price(self, symbol):
        return SIM_PRICES.get(symbol, DEFAULT_SIM_PRICE)

    def set_leverage(self, symbol, leverage):
        print(f"[SIM] Set leverage to {leverage}x")

    def place_market_order(self, symbol, side, amount):
        price = self.get_market_price(symbol)
        print(f"[SIM] Placed {side.upper()} order: {amount} {symbol} at {price}")
        return {"id": "SIMULATED_ORDER"}

    def place_limit_order(self, symbol, side, price, amount):
        print(f"[SIM] Placed LIMIT {side.upper()} order: {amount} {symbol} at ${price}")
        return {"id": "SIMULATED_LIMIT_ORDER"}

    def place_stop_loss(self, symbol, side, stop_price, amount):
        print(f"[SIM] Set SL at ${stop_price} for {amount} {symbol}")
        return {"id": "SIMULATED_SL"}
