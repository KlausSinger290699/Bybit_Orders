import ccxt

# ===== CONFIG =====
API_KEY = "x6d9o7hQVoR1R9MQja"
API_SECRET = "Rj145VpvkogrSgnhSf7KGUdJr9Cdscw2vv7t"
SYMBOL = "BTC/USDT:USDT"

exchange = ccxt.bybit({
    "apiKey": API_KEY,
    "secret": API_SECRET,
    "enableRateLimit": True,
})
exchange.set_sandbox_mode(True)
exchange.options["defaultType"] = "future"
exchange.load_markets()

# ===== simple test functions =====
def test_balance():
    bal = exchange.fetch_balance()
    print("Balance USDT:", bal["total"]["USDT"])

def test_market_price():
    price = exchange.fetch_ticker(SYMBOL)["last"]
    print(f"Market price {SYMBOL}:", price)

def test_market_order():
    out = exchange.create_order(SYMBOL, "market", "buy", 0.001)
    print("Market order result:", out)

def test_limit_order():
    last = exchange.fetch_ticker(SYMBOL)["last"]
    price = round(last * 0.95, 2)
    out = exchange.create_order(SYMBOL, "limit", "buy", 0.001, price, {"postOnly": True})
    print("Limit order result:", out)

def test_stop_loss():
    last = exchange.fetch_ticker(SYMBOL)["last"]
    stop = round(last * 0.95, 2)
    out = exchange.create_order(SYMBOL, "market", "sell", 0.001, None, {
        "reduceOnly": True, "stopPrice": stop
    })
    print("Stop-loss order result:", out)

def test_set_leverage():
    try:
        out = exchange.set_leverage(2, SYMBOL)
    except Exception:
        m = exchange.market(SYMBOL)
        out = exchange.privatePostV5PositionSetLeverage({
            "category": "linear",
            "symbol": m["id"],
            "buyLeverage": "2",
            "sellLeverage": "2",
        })
    print("Set leverage result:", out)


# ===== interactive menu =====
actions = {
    "1": ("Check balance", test_balance),
    "2": ("Check market price", test_market_price),
    "3": ("Place market order", test_market_order),
    "4": ("Place limit order", test_limit_order),
    "5": ("Place stop-loss", test_stop_loss),
    "6": ("Set leverage", test_set_leverage),
}

if __name__ == "__main__":
    print("\nChoose test:")
    for k, (desc, _) in actions.items():
        print(f"{k}. {desc}")

    choice = input("Enter number: ").strip()
    if choice in actions:
        actions[choice][1]()
    else:
        print("Invalid choice")
