# enums.py
from enum import Enum

class OrderType(str, Enum):
    MARKET = "market"
    LIMIT  = "limit"
