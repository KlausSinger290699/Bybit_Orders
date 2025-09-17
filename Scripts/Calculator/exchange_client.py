import time
import ccxt
from dependency_injector.wiring import Provide, inject
from container import Container
from enums import OrderType
from models import TradeConfig, TradeParams
from order_calculator import calculate_position_sizing, plan_pyramid_tranches

API_KEY         = "JVyNFG6yyMvD7zucnP"
API_SECRET      = "9dOWIBweh9EZKCnll6Pc1CSUaJ9xs9CStzSo"
DEMO_TRADING    = True
DEFAULT_TYPE    = "future"
DEFAULT_EXID    = "bybit"
QUOTE           = "USDT"
CONTRACT_SUFFIX = ":USDT"

ORDER_TAG = "NX"

ACCOUNTS: list[dict] = [
    {"name":"BybitTest1","exchange_id":"bybit","api_key":"JVyNFG6yyMvD7zucnP","api_secret":"9dOWIBweh9EZKCnll6Pc1CSUaJ9xs9CStzSo","demo":True,"default_type":"future"},
    {"name":"BybitTest2","exchange_id":"bybit","api_key":"jiSLuypK1EWZK9eHMy","api_secret":"ulFbMvZN5b5gXeieuJbhi2F9eXrBahybGaUm","demo":True,"default_type":"future"},
]
DISPLAY_INDEX = 0


class SingleExchangeClient:
    def __init__(self, *, api_key: str, api_secret: str, demo_trading: bool, default_type: str, exchange_id: str, name: str | None = None):
        ex_class = getattr(ccxt, exchange_id)
        self.exchange = ex_class({"apiKey": api_key, "secret": api_secret, "enableRateLimit": True})
        self.name = name or getattr(self.exchange, "id", exchange_id)
        self.exchange.enable_demo_trading(bool(demo_trading))
        self.exchange.options["defaultType"] = default_type
        print(f"Loading markets ({self.name} | {'testnet' if demo_trading else 'live'})...")
        self.exchange.load_markets()
        self._force_hedge_mode()
        print("Ready.\n")

    # ---- basics ----
    def symbol_for(self, ticker: str) -> str:
        return f"{ticker.strip().upper()}/{QUOTE}{CONTRACT_SUFFIX}"

    def get_balance_usdt(self) -> float:
        bal = self.exchange.fetch_balance()
        return float(bal["total"]["USDT"])

    def get_market_price(self, ticker: str) -> float:
        symbol = self.symbol_for(ticker)
        return float(self.exchange.fetch_ticker(symbol)["last"])

    def get_current_leverage(self, symbol: str) -> float | None:
        try:
            try:
                positions = self.exchange.fetch_positions([symbol])
            except Exception:
                positions = self.exchange.fetch_positions()
            if isinstance(positions, list):
                for p in positions:
                    if p.get("symbol") == symbol:
                        lev = p.get("leverage") or (p.get("info", {}) or {}).get("leverage")
                        return float(lev) if lev else None
            elif isinstance(positions, dict):
                lev = positions.get("leverage") or (positions.get("info", {}) or {}).get("leverage")
                return float(lev) if lev else None
        except Exception:
            return None
        return None

    def _force_hedge_mode(self) -> None:
        try:
            self.exchange.set_position_mode(True)
        except Exception:
            pass
        try:
            if hasattr(self.exchange, "fetch_position_mode"):
                info = self.exchange.fetch_position_mode()
                if not bool(info.get("hedged", True)):
                    try: self.exchange.set_position_mode(True)
                    except Exception: pass
        except Exception:
            pass

    @staticmethod
    def _position_idx_for_side(side: str) -> int:
        return 1 if side.lower() == "buy" else 2

    def _cid(self, group_key: str | None = None) -> str:
        ts = int(time.time() * 1000)
        base = f"{ORDER_TAG}-{group_key}-{self.name}" if group_key else f"{ORDER_TAG}-{self.name}"
        return f"{base}-{ts}"

    # ---- leverage (non-DI, explicit) ----
    def set_leverage(self, *, symbol: str, leverage: float):
        if leverage is None or float(leverage) <= 0:
            return {"skipped": "no leverage requested"}
        lev_int = int(float(leverage))
        current = self.get_current_leverage(symbol)
        if current is not None and int(float(current)) == lev_int:
            return {"skipped": "leverage already set"}
        return self.exchange.set_leverage(lev_int, symbol)

    # ---- leverage (DI-based; kept for single-shot flows) ----
    @inject
    def apply_leverage(self, config: TradeConfig = Provide[Container.trade_config], params: TradeParams = Provide[Container.trade_params]):
        desired = params.leverage
        if desired is None or desired == "" or float(desired) <= 0:
            return {"skipped": "no leverage requested"}
        desired_int = int(float(desired))
        current = self.get_current_leverage(config.symbol)
        if current is not None and int(float(current)) == desired_int:
            return {"skipped": "leverage already set"}
        try:
            return self.exchange.set_leverage(desired_int, config.symbol)
        except ccxt.BadRequest as e:
            msg = str(e)
            if "110043" in msg or "leverage not modified" in msg.lower():
                return {"ignored": "leverage not modified"}
            raise

    # ---- order helpers (explicit params for pyramid) ----
    def create_market_with_stop(self, *, symbol: str, side: str, amount: float, stop: float, group_key: str | None = None):
        amt = float(self.exchange.amount_to_precision(symbol, amount))
        sl  = self.exchange.price_to_precision(symbol, stop)
        return self.exchange.create_order(
            symbol, "market", side, amt, None,
            {"clientOrderId": self._cid(group_key), "positionIdx": self._position_idx_for_side(side), "stopLoss": sl, "slTriggerBy": "LastPrice", "tpslMode": "Full"}
        )

    def create_limit_with_stop(self, *, symbol: str, side: str, amount: float, price: float, stop: float, post_only: bool = True, group_key: str | None = None):
        amt = float(self.exchange.amount_to_precision(symbol, amount))
        px  = self.exchange.price_to_precision(symbol, float(price))
        sl  = self.exchange.price_to_precision(symbol, stop)
        return self.exchange.create_order(
            symbol, "limit", side, amt, px,
            {"clientOrderId": self._cid(group_key), "postOnly": post_only, "positionIdx": self._position_idx_for_side(side), "stopLoss": sl, "slTriggerBy": "LastPrice", "tpslMode": "Full"}
        )

    # ---- DI single-shot (kept for existing flow) ----
    @inject
    def market_order_with_stop(self, side: str, amount: float, config: TradeConfig = Provide[Container.trade_config], params: TradeParams = Provide[Container.trade_params]):
        symbol = config.symbol
        sl_px  = params.stop_loss_price
        amt = float(self.exchange.amount_to_precision(symbol, amount))
        sl  = self.exchange.price_to_precision(symbol, sl_px)
        return self.exchange.create_order(symbol, "market", side, amt, None, {"positionIdx": self._position_idx_for_side(side), "stopLoss": sl, "slTriggerBy": "LastPrice", "tpslMode": "Full"})

    @inject
    def limit_order_with_stop(self, side: str, amount: float, config: TradeConfig = Provide[Container.trade_config], params: TradeParams = Provide[Container.trade_params]):
        symbol = config.symbol
        entry  = params.entry_price
        sl_px  = params.stop_loss_price
        if entry is None:
            raise ValueError("entry_price must be provided for LIMIT orders.")
        amt = float(self.exchange.amount_to_precision(symbol, amount))
        px  = self.exchange.price_to_precision(symbol, float(entry))
        sl  = self.exchange.price_to_precision(symbol, sl_px)
        return self.exchange.create_order(symbol, "limit", side, amt, px, {"postOnly": True, "positionIdx": self._position_idx_for_side(side), "stopLoss": sl, "slTriggerBy": "LastPrice", "tpslMode": "Full"})

    # ---- order management (unchanged) ----
    def fetch_open_orders(self, symbol: str | None = None) -> list[dict]:
        try: return self.exchange.fetch_open_orders(symbol)
        except Exception: return []

    def cancel_order_by_key(self, order_key: str, symbol: str | None = None) -> dict:
        try:
            return {"ok": True, "resp": self.exchange.cancel_order(order_key, symbol)}
        except Exception:
            pass
        opens = self.fetch_open_orders(symbol)
        for o in opens:
            cid = (o.get("clientOrderId") or "").strip()
            oid = (o.get("id") or "").strip()
            if order_key == cid or order_key == oid:
                try: return {"ok": True, "resp": self.exchange.cancel_order(oid or order_key, symbol)}
                except Exception as e: return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "not found among open orders"}

    def cancel_all_ours(self, symbol: str | None = None) -> dict:
        cancelled, errors = [], []
        for o in self.fetch_open_orders(symbol):
            cid = (o.get("clientOrderId") or "")
            if cid.startswith(ORDER_TAG):
                oid = o.get("id")
                try:
                    resp = self.exchange.cancel_order(oid, symbol)
                    cancelled.append({"id": oid, "clientOrderId": cid, "resp": resp})
                except Exception as e:
                    errors.append({"id": oid, "clientOrderId": cid, "error": str(e)})
        return {"ok": len(errors) == 0, "cancelled": cancelled, "errors": errors}

    def cancel_all_open_orders(self, symbol: str | None = None) -> dict:
        try:
            if hasattr(self.exchange, "cancel_all_orders"):
                resp = self.exchange.cancel_all_orders(symbol)
                return {"ok": True, "resp": resp}
        except Exception:
            pass
        cancelled, errors = [], []
        for o in self.fetch_open_orders(symbol):
            oid = o.get("id")
            try:
                resp = self.exchange.cancel_order(oid, symbol)
                cancelled.append({"id": oid, "resp": resp})
            except Exception as e:
                errors.append({"id": oid, "error": str(e)})
        return {"ok": len(errors) == 0, "cancelled": cancelled, "errors": errors}

    def close_all_positions(self, symbol: str | None = None) -> dict:
        closed, errors = [], []
        try:
            positions = self.exchange.fetch_positions([symbol]) if symbol else self.exchange.fetch_positions()
        except Exception as e:
            return {"ok": False, "error": f"fetch_positions failed: {e}"}

        def _reduce(symbol: str, side: str, amount: float, position_idx: int):
            try:
                amt = float(self.exchange.amount_to_precision(symbol, amount))
                params = {"reduceOnly": True, "positionIdx": position_idx}
                resp = self.exchange.create_order(symbol, "market", side, amt, None, params)
                closed.append({"symbol": symbol, "side": side, "amount": amt, "resp": resp})
            except Exception as e:
                errors.append({"symbol": symbol, "side": side, "error": str(e)})

        for p in positions or []:
            sym = p.get("symbol")
            contracts = abs(float(p.get("contracts") or p.get("contractSize") or p.get("amount") or 0))
            if contracts <= 0:
                continue
            side = (p.get("side") or "").lower()
            if side == "long":
                _reduce(sym, "sell", contracts, 1)
            elif side == "short":
                _reduce(sym, "buy", contracts, 2)
        return {"ok": len(errors) == 0, "closed": closed, "errors": errors}


class ExchangeClient:
    """Facade; calculator only talks to this."""
    def __init__(self):
        self._clients: list[SingleExchangeClient] = []
        if ACCOUNTS:
            for acc in ACCOUNTS:
                self._clients.append(SingleExchangeClient(
                    api_key=acc["api_key"], api_secret=acc["api_secret"],
                    demo_trading=bool(acc.get("demo", DEMO_TRADING)),
                    default_type=acc.get("default_type", DEFAULT_TYPE),
                    exchange_id=acc.get("exchange_id", DEFAULT_EXID),
                    name=acc.get("name"),
                ))
        else:
            self._clients.append(SingleExchangeClient(
                api_key=API_KEY, api_secret=API_SECRET, demo_trading=DEMO_TRADING,
                default_type=DEFAULT_TYPE, exchange_id=DEFAULT_EXID, name="primary",
            ))
        self._display_index = DISPLAY_INDEX if DISPLAY_INDEX < len(self._clients) else 0

        required = ("get_balance_usdt","get_market_price","get_current_leverage","market_order_with_stop",
                    "limit_order_with_stop","apply_leverage","symbol_for","fetch_open_orders",
                    "cancel_order_by_key","cancel_all_ours","cancel_all_open_orders","close_all_positions",
                    "create_market_with_stop","create_limit_with_stop","set_leverage")
        for c in self._clients:
            for attr in required:
                if not hasattr(c, attr):
                    raise AttributeError(f"{c.__class__.__name__} missing required method: {attr}")

    @property
    def primary(self) -> SingleExchangeClient: return self._clients[self._display_index]
    def symbol_for(self, ticker: str) -> str:  return self.primary.symbol_for(ticker)
    def get_balance_usdt(self) -> float:        return self.primary.get_balance_usdt()
    def get_market_price(self, ticker: str) -> float: return self.primary.get_market_price(ticker)
    def get_current_leverage(self, symbol: str) -> float | None: return self.primary.get_current_leverage(symbol)
    def name(self) -> str:                      return self.primary.name
    def preview_primary_sizing(self, balance_usdt: float) -> dict: return calculate_position_sizing(balance_usdt)

    # ---- submit single (existing) ----
    def submit_all(self, order_type: OrderType, side: str) -> list[dict]:
        results: list[dict] = []
        for c in self._clients:
            try:
                bal = c.get_balance_usdt()
                sizing = calculate_position_sizing(bal)
                amt = sizing["position_size"]; r_usd = sizing["risk_usdt"]
                c.apply_leverage()
                if order_type == OrderType.MARKET:
                    resp = c.market_order_with_stop(side=side, amount=amt)
                else:
                    resp = c.limit_order_with_stop(side=side, amount=amt)
                results.append({"name": c.name, "ok": True, "id": resp.get("id", resp), "amount": amt, "risk_usd": r_usd})
            except Exception as e:
                results.append({"name": c.name, "ok": False, "error": str(e)})
        return results

    # ---- pyramid across all accounts (passes risk_shape) ----
    def submit_pyramid(
        self,
        *,
        base: str,
        stop_price: float,
        leverage: float,
        risk_percent: float,
        top_price: float | None,
        bottom_price: float,
        levels: int,
        immediate_risk_pct: float,
        post_only_limits: bool = True,
        risk_shape: float = 1.0,
    ) -> list[dict]:
        symbol = self.symbol_for(base)
        group_key = f"PYR-{int(time.time()*1000)}"
        out: list[dict] = []

        for c in self._clients:
            try:
                bal = c.get_balance_usdt()
                live_px = c.get_market_price(base)

                plan = plan_pyramid_tranches(
                    balance_usdt=bal,
                    risk_percent=risk_percent,
                    stop_price=stop_price,
                    leverage=leverage,
                    top_price=top_price,
                    bottom_price=bottom_price,
                    live_price=live_px,
                    levels=levels,
                    immediate_risk_pct=immediate_risk_pct,
                    risk_shape=risk_shape,
                )
                side = "buy" if plan["side"] == "long" else "sell"

                c.set_leverage(symbol=symbol, leverage=leverage)

                placed = []
                for t in plan["tranches"]:
                    qty = t["qty"]
                    if t["type"] == "market":
                        resp = c.create_market_with_stop(symbol=symbol, side=side, amount=qty, stop=stop_price, group_key=group_key)
                    else:
                        resp = c.create_limit_with_stop(symbol=symbol, side=side, amount=qty, price=t["price"], stop=stop_price, post_only=post_only_limits, group_key=group_key)
                    placed.append({"id": resp.get("id", resp), "type": t["type"], "price": round(t["price"], 6), "qty": round(qty, 6)})

                out.append({
                    "name": c.name,
                    "ok": True,
                    "side": plan["side"],
                    "levels": levels,
                    "immediate_pct": immediate_risk_pct,
                    "totals": plan["totals"],
                    "shape": plan["meta"]["risk_shape"],
                    "orders": placed,
                })
            except Exception as e:
                out.append({"name": c.name, "ok": False, "error": str(e)})
        return out

    # ---- cancels/close (unchanged wrappers) ----
    def cancel_specific_everywhere(self, order_key: str, symbol: str | None = None) -> list[dict]:
        return [{"name": c.name, **c.cancel_order_by_key(order_key, symbol)} for c in self._clients]

    def cancel_all_ours(self, symbol: str | None = None) -> list[dict]:
        return [{"name": c.name, **c.cancel_all_ours(symbol)} for c in self._clients]

    def cancel_all_everywhere(self, symbol: str | None = None) -> list[dict]:
        return [{"name": c.name, **c.cancel_all_open_orders(symbol)} for c in self._clients]

    def close_all_positions(self, symbol: str | None = None) -> list[dict]:
        return [{"name": c.name, **c.close_all_positions(symbol)} for c in self._clients]
