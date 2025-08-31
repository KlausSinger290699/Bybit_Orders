from dataclasses import dataclass
from enums import OrderType

@dataclass
class TradeConfig:
    simulate_mode: bool          
    symbol: str                  
    order_type: OrderType

@dataclass
class TradeParams:
    stop_loss_price: float
    risk_percent: float
    leverage: float
    entry_price: float | None    

@dataclass
class OrderPlan:
    symbol: str
    order_type: OrderType
    side: str            
    amount: float        
    stop_loss_price: float
    entry_price: float | None
    leverage: float