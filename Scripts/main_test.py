import ccxt 

API_KEY = "x6d9o7hQVoR1R9MQja"
API_SECRET = "Rj145VpvkogrSgnhSf7KGUdJr9Cdscw2vv7t"

exchange_id = 'bybit'
exchange_class = getattr(ccxt, exchange_id)
exchange = exchange_class({
    "apiKey": API_KEY,
    "secret": API_SECRET,
})

exchange.enable_demo_trading(True)

exchange.options['defaultType'] = 'future'
exchange.load_markets()

response = exchange.fetch_balance()
print(response['USDT'])