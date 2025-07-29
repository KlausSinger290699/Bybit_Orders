import ccxt

def create_client(config):
    client = ccxt.bybit({
        'apiKey': config["apiKey"],
        'secret': config["secret"],
        'enableRateLimit': True,
        'options': {'defaultType': 'linear'}
    })
    client.set_sandbox_mode(config["sandbox"])
    if config["sandbox"]:
        client.urls['api'] = client.urls['test']
    return client

def get_balance_usdt(client):
    balance = client.fetch_balance()
    return balance['total']['USDT']

def get_price(client, symbol):
    ticker = client.fetch_ticker(symbol)
    return ticker['last']

def place_market_order(client, symbol, side, amount):
    return client.create_order(symbol=symbol, type='market', side=side, amount=amount)

def set_leverage(client, symbol, leverage):
    market = client.market(symbol)
    client.private_linear_post_position_set_leverage({
        "symbol": market["id"],
        "buy_leverage": leverage,
        "sell_leverage": leverage
    })

    # Optional validation (can be removed if too slow)
    leverage_info = client.private_linear_get_position_list({'symbol': market['id']})
    current_leverage = leverage_info['result'][0]['leverage']
    print(f"✅ Leverage for {symbol} confirmed: {current_leverage}x")
