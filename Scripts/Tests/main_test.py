import ccxt 

API_KEY = "JVyNFG6yyMvD7zucnP"
API_SECRET = "9dOWIBweh9EZKCnll6Pc1CSUaJ9xs9CStzSo"

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