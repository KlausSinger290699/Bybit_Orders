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
