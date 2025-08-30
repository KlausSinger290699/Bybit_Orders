from enum import Enum

class TradingSymbol(str, Enum):
    BTC = "BTC/USDT"
    ETH = "ETH/USDT"
    SOL = "SOL/USDT"
    XRP = "XRP/USDT"
    DOGE = "DOGE/USDT"

class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
