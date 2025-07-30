import ccxt
import random

class ExchangeClient:
    def get_balance_usdt(self): raise NotImplementedError
    def get_market_price(self, symbol): raise NotImplementedError
    def set_leverage(self, symbol, leverage): raise NotImplementedError
    def place_market_order(self, symbol, side, amount): raise NotImplementedError
    def place_stop_loss(self, symbol, side, stop_price, amount): raise NotImplementedError

class BybitClient(ExchangeClient):
    def __init__(self, config):
        self.client = ccxt.bybit({
            'apiKey': config["apiKey"],
            'secret': config["secret"],
            'enableRateLimit': True,
            'options': {'defaultType': 'linear'}
        })
        self.client.set_sandbox_mode(config["sandbox"])
        if config["sandbox"]:
            self.client.urls['api'] = self.client.urls['test']
        self.symbol = config["symbol"]

    def get_balance_usdt(self):
        return self.client.fetch_balance()['total']['USDT']

    def get_market_price(self, symbol):
        return self.client.fetch_ticker(symbol)['last']

    def set_leverage(self, symbol, leverage):
        market = self.client.market(symbol)
        self.client.private_linear_post_position_set_leverage({
            "symbol": market["id"],
            "buy_leverage": leverage,
            "sell_leverage": leverage
        })

    def place_market_order(self, symbol, side, amount):
        return self.client.create_order(symbol=symbol, type='market', side=side, amount=amount)

    def place_stop_loss(self, symbol, side, stop_price, amount):
        opposite = "sell" if side == "buy" else "buy"
        return self.client.create_order(symbol=symbol, type='stop_market', side=opposite,
                                        amount=amount, params={"stop_loss": stop_price})


class SimulatedClient(ExchangeClient):
    def __init__(self, config):
        self._symbol = config["symbol"]
        self._last_price = 50000
        self._fake_balance = 10000

    def get_balance_usdt(self):
        return self._fake_balance

    def get_market_price(self, symbol):
        return self._last_price

    def set_leverage(self, symbol, leverage):
        print(f"[SIM] Set leverage to {leverage}x")

    def place_market_order(self, symbol, side, amount):
        print(f"[SIM] Placed {side.upper()} order: {amount} {symbol} at {self._last_price}")
        return {"id": "SIMULATED_ORDER"}

    def place_stop_loss(self, symbol, side, stop_price, amount):
        print(f"[SIM] Set SL at ${stop_price} for {amount} {symbol}")
        return {"id": "SIMULATED_SL"}

