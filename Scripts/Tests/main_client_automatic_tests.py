from exchange_client import BybitClient

# ===== config =====
CONFIG = {
    "apiKey": "JVyNFG6yyMvD7zucnP",
    "secret": "9dOWIBweh9EZKCnll6Pc1CSUaJ9xs9CStzSo",
    "sandbox": True,
}
SYMBOL = "RUNE/USDT:USDT"
TEST_LEVERAGE = 2
TEST_AMOUNT = 0.001


# ===== test runner =====
class ClientSmokeTester:
    def __init__(self, client, symbol, leverage, amount):
        self.client = client
        self.symbol = symbol
        self.leverage = leverage
        self.amount = amount

    def _safe(self, label, fn):
        print(f"\n[{label}]")
        try:
            out = fn()
            print("OK:", out)
        except Exception as e:
            print("ERR:", repr(e))

    def run(self):
        self._safe("balance", lambda: self.client.get_balance_usdt())
        self._safe("market_price", lambda: self.client.get_market_price(self.symbol))
        self._safe("set_leverage", lambda: self.client.set_leverage(self.symbol, self.leverage))

        def limit_far():
            last = self.client.get_market_price(self.symbol)
            price = round(last * 0.5, 2)
            return self.client.place_limit_order(self.symbol, "buy", price, self.amount)
        self._safe("limit_order_postonly_far", limit_far)

        self._safe("market_order_buy", lambda: self.client.place_market_order(self.symbol, "buy", self.amount))

        def stop_loss_for_long():
            last = self.client.get_market_price(self.symbol)
            stop = round(last * 0.95, 2)
            return self.client.place_stop_loss(self.symbol, "buy", stop, self.amount)
        self._safe("stop_loss_for_long", stop_loss_for_long)

        print("\nDone.")


# ===== entrypoints =====
if __name__ == "__main__":
    # assumes BybitClient / SimulatedClient are already defined above in this file
    bybit = BybitClient(CONFIG)
    ClientSmokeTester(bybit, SYMBOL, TEST_LEVERAGE, TEST_AMOUNT).run()

    # Uncomment to compare with simulation using the same interface:
    # sim = SimulatedClient(CONFIG)
    # ClientSmokeTester(sim, SYMBOL, TEST_LEVERAGE, TEST_AMOUNT).run()
