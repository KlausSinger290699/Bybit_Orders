class TradeClient:
    def get_balance_usdt(self):
        raise NotImplementedError

    def set_leverage(self, symbol, leverage):
        raise NotImplementedError

    def place_market_order(self, symbol, side, amount):
        raise NotImplementedError
