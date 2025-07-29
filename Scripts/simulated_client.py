from trade_interface import TradeClient

class SimulatedClient(TradeClient):
    def __init__(self, balance):
        self.balance = balance

    def get_balance_usdt(self):
        return self.balance

    def set_leverage(self, symbol, leverage):
        print(f"🛠️  Simulated setting leverage to {leverage}x for {symbol}")

    def place_market_order(self, symbol, side, amount):
        print(f"[SIMULATED] {side.upper()} {amount} {symbol}")
        return {"id": "SIM-ORDER-123"}
