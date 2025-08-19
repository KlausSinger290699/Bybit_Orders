import ccxt

API_KEY = "x6d9o7hQVoR1R9MQja"
API_SECRET = "Rj145VpvkogrSgnhSf7KGUdJr9Cdscw2vv7t"

SYMBOL = "ETH/USDT"
TEST_LEVERAGE = 2
TEST_AMOUNT = 0.01  # adjust if your min size differs

def safe(label, fn):
    print(f"\n[{label}]")
    try:
        out = fn()
        print("OK:", out)
    except Exception as e:
        print("ERR:", repr(e))

def mk_client():
    ex = ccxt.bybit({
        "apiKey": API_KEY,
        "secret": API_SECRET,
        "enableRateLimit": True,
        "options": {"defaultType": "linear"},
    })
    ex.set_sandbox_mode(True)
    ex.load_markets()
    return ex

def test_balance(ex):
    bal = ex.fetch_balance()
    return {"USDT_total": bal["total"].get("USDT", 0), "USDT_free": bal["free"].get("USDT", 0)}

def test_price(ex, symbol):
    return ex.fetch_ticker(symbol)["last"]

def test_set_leverage(ex, symbol, lev):
    try:
        return ex.set_leverage(lev, symbol)
    except Exception:
        m = ex.market(symbol)
        try:
            return ex.privatePostV5PositionSetLeverage({
                "category": "linear",
                "symbol": m["id"],
                "buyLeverage": str(lev),
                "sellLeverage": str(lev),
            })
        except Exception:
            return ex.privateLinearPostPositionSetLeverage({
                "symbol": m["id"],
                "buy_leverage": lev,
                "sell_leverage": lev,
            })

def test_limit_postonly(ex, symbol, side, price, amount):
    try:
        return ex.create_order(symbol, "limit", side, amount, price, {"postOnly": True})
    except Exception:
        return ex.create_order(symbol, "limit", side, amount, price, {"timeInForce": "PostOnly"})

def test_market_order(ex, symbol, side, amount):
    return ex.create_order(symbol, "market", side, amount)

def test_stop_loss(ex, symbol, side, stop_price, amount):
    opposite = "sell" if side == "buy" else "buy"
    tries = [
        {"reduceOnly": True, "triggerPrice": stop_price},
        {"reduceOnly": True, "stopPrice": stop_price},
        {"reduceOnly": True, "stopLossPrice": stop_price},
        {"reduceOnly": True, "price": None, "triggerPrice": stop_price, "orderType": "Market"},
    ]
    last_err = None
    for params in tries:
        try:
            return ex.create_order(symbol, "market", opposite, amount, None, params)
        except Exception as e:
            last_err = e
    raise last_err

if __name__ == "__main__":
    ex = mk_client()

    safe("balance", lambda: test_balance(ex))

    price_holder = {"last": None}
    def step_price():
        price_holder["last"] = test_price(ex, SYMBOL)
        return price_holder["last"]
    safe("market_price", step_price)

    safe("set_leverage", lambda: test_set_leverage(ex, SYMBOL, TEST_LEVERAGE))

    def limit_far():
        p = price_holder["last"] or test_price(ex, SYMBOL)
        return test_limit_postonly(ex, SYMBOL, "buy", round(p * 0.5, 2), TEST_AMOUNT)
    safe("limit_postonly_far", limit_far)

    safe("market_order_buy", lambda: test_market_order(ex, SYMBOL, "buy", TEST_AMOUNT))

    def stop_for_long():
        p = price_holder["last"] or test_price(ex, SYMBOL)
        return test_stop_loss(ex, SYMBOL, "buy", round(p * 0.95, 2), TEST_AMOUNT)
    safe("stop_loss_for_long", stop_for_long)

    print("\nDone.")
