from enums import TradingSymbol, OrderType

TEST_PRESETS = {
    "quick_btc_market": {
        "simulate_mode": True,
        "symbol": TradingSymbol.BTC.value,
        "order_type": OrderType.MARKET,
        "entry_price": None,
        "stop_loss_price": 46000.0,
        "risk_percent": 1.0,
        "leverage": 10.0
    },
    "eth_limit_test": {
        "simulate_mode": True,
        "symbol": TradingSymbol.ETH.value,
        "order_type": OrderType.LIMIT,
        "entry_price": 3100.0,
        "stop_loss_price": 2900.0,
        "risk_percent": 2.0,
        "leverage": 5.0
    }
}