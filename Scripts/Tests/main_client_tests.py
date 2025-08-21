import ccxt

# ===== CONFIG =====
API_KEY = "JVyNFG6yyMvD7zucnP"
API_SECRET = "9dOWIBweh9EZKCnll6Pc1CSUaJ9xs9CStzSo"
SYMBOL = "RUNE/USDT:USDT"

exchange = ccxt.bybit({
    "apiKey": API_KEY,
    "secret": API_SECRET,
    "enableRateLimit": True,
})
exchange.enable_demo_trading(True)
exchange.options["defaultType"] = "future"

print("Loading markets (testnet)...")
exchange.load_markets()
print("Ready.\n")

# ===== simple test functions =====
def test_balance():
    bal = exchange.fetch_balance()
    print("Balance USDT:", bal["total"]["USDT"])

def test_market_price():
    price = exchange.fetch_ticker(SYMBOL)["last"]
    print(f"Market price {SYMBOL}:", price)

def test_market_order():
    amount = exchange.amount_to_precision(SYMBOL, 0.1)
    exchange.create_order(SYMBOL, "market", "buy", amount, None, {"positionIdx": 1})
    rough = exchange.fetch_ticker(SYMBOL)["last"]
    print(f"Market fill ~ {exchange.price_to_precision(SYMBOL, rough)}")

def test_limit_order():
    last = exchange.fetch_ticker(SYMBOL)["last"]
    amount = exchange.amount_to_precision(SYMBOL, 0.1)
    target = last * 0.95
    price = exchange.price_to_precision(SYMBOL, target)
    exchange.create_order(SYMBOL, "limit", "buy", amount, price, {"postOnly": True, "positionIdx": 1})
    pct = ((float(price) - last) / last) * 100
    print(f"Limit @ {price} ({pct:+.2f}%)")

def test_stop_loss():
    last = exchange.fetch_ticker(SYMBOL)["last"]
    amount = exchange.amount_to_precision(SYMBOL, 0.1)
    stop = exchange.price_to_precision(SYMBOL, last * 0.95)
    exchange.create_order(
        SYMBOL, "market", "sell", amount, None,
        {"reduceOnly": True, "stopPrice": stop, "triggerDirection": "descending", "positionIdx": 1}
    )
    print(f"Stop-loss @ {stop}")

def test_set_leverage():
    try:
        out = exchange.set_leverage(2, SYMBOL)
        if isinstance(out, dict):
            code = str(out.get("retCode"))
            if code == "110043":
                print("Leverage already set to 2x"); return
            if code == "0":
                print("Leverage successfully set to 2x"); return
        print("Set leverage result:", out)
    except Exception as e:
        msg = str(e)
        if "110043" in msg or "leverage not modified" in msg:
            print("Leverage already set to 2x")
        else:
            print("Error setting leverage:", msg)

def test_market_order_with_stop_loss():
    last   = exchange.fetch_ticker(SYMBOL)["last"]
    amount = exchange.amount_to_precision(SYMBOL, 0.1)
    sl     = exchange.price_to_precision(SYMBOL, last * 0.95)

    exchange.create_order(
        SYMBOL, "market", "buy", amount, None,
        {"positionIdx": 1, "stopLoss": sl, "slTriggerBy": "LastPrice", "tpslMode": "Full"}
    )

    entry = exchange.fetch_ticker(SYMBOL)["last"]
    entry_str = exchange.price_to_precision(SYMBOL, entry)
    sl_pct_vs_entry = ((float(sl) - entry) / entry) * 100
    print(f"Market+SL: entry ~ {entry_str} | SL {sl} ({sl_pct_vs_entry:+.2f}% vs entry)")

def test_limit_order_with_stop_loss():
    last   = exchange.fetch_ticker(SYMBOL)["last"]
    amount = exchange.amount_to_precision(SYMBOL, 0.1)
    price  = exchange.price_to_precision(SYMBOL, last * 0.95)      # entry target
    sl     = exchange.price_to_precision(SYMBOL, float(price) * 0.98)

    exchange.create_order(
        SYMBOL, "limit", "buy", amount, price,
        {"postOnly": True, "positionIdx": 1, "stopLoss": sl, "slTriggerBy": "LastPrice", "tpslMode": "Full"}
    )

    pct_curr = ((float(price) - last) / last) * 100
    pct_sl_entry = ((float(sl) - float(price)) / float(price)) * 100
    print(f"Limit+SL: entry {price} ({pct_curr:+.2f}% vs market) | SL {sl} ({pct_sl_entry:+.2f}% vs entry)")


# ===== interactive menu =====
actions = {
    "1": ("Check balance", test_balance),
    "2": ("Check market price", test_market_price),
    "3": ("Place market order", test_market_order),
    "4": ("Place limit order", test_limit_order),
    "5": ("Place stop-loss", test_stop_loss),
    "6": ("Set leverage", test_set_leverage),
    "7": ("Market + Stop-Loss (TP/SL section)", test_market_order_with_stop_loss),
    "8": ("Limit + Stop-Loss (TP/SL section)", test_limit_order_with_stop_loss),
    "q": ("Quit", None),
}

if __name__ == "__main__":
    while True:
        print("\nChoose test:")
        for k, (desc, _) in actions.items():
            print(f"{k}. {desc}")
        choice = input("Enter number: ").strip().lower()
        if choice == "q":
            break
        elif choice in actions:
            try:
                actions[choice][1]()
            except Exception as e:
                print("Error:", e)
        else:
            print("Invalid choice")
        input("Press Enter to continue . . .")
