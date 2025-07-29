import ccxt
from trade_interface import TradeClient

class RealBybitClient(TradeClient):
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

    def set_leverage(self, symbol, leverage):
        market = self.client.market(symbol)
        self.client.private_linear_post_position_set_leverage({
            "symbol": market["id"],
            "buy_leverage": leverage,
            "sell_leverage": leverage
        })

        leverage_info = self.client.private_linear_get_position_list({'symbol': market['id']})
        current_leverage = leverage_info['result'][0]['leverage']
        print(f"✅ Leverage confirmed: {current_leverage}x")

    def place_market_order(self, symbol, side, amount):
        return self.client.create_order(symbol=symbol, type='market', side=side, amount=amount)
