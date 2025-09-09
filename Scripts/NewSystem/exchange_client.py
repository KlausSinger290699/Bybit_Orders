import time
import ccxt
from dependency_injector.wiring import Provide, inject
from container import Container
from enums import OrderType
from models import TradeConfig, TradeParams
from order_calculator import calculate_position_sizing

API_KEY         = "JVyNFG6yyMvD7zucnP"
API_SECRET      = "9dOWIBweh9EZKCnll6Pc1CSUaJ9xs9CStzSo"
DEMO_TRADING    = True
DEFAULT_TYPE    = "future"
DEFAULT_EXID    = "bybit"
QUOTE           = "USDT"
CONTRACT_SUFFIX = ":USDT"

# All orders placed by this software are tagged with this prefix.
ORDER_TAG = "NX"  # change if you want a different signature

ACCOUNTS: list[dict] = [
    {
        "name": "BybitTest1",
        "exchange_id": "bybit",
        "api_key": "JVyNFG6yyMvD7zucnP",
        "api_secret": "9dOWIBweh9EZKCnll6Pc1CSUaJ9xs9CStzSo",
        "demo": True,
        "default_type": "future",
    },
    {
        "name": "BybitTest2",
        "exchange_id": "bybit",
        "api_key": "jiSLuypK1EWZK9eHMy",
        "api_secret": "ulFbMvZN5b5gXeieuJbhi2F9eXrBahybGaUm",
        "demo": True,
        "default_type": "future",
    },
]
DISPLAY_INDEX = 0


class SingleExchangeClient:
    def __init__(
        self,
        *,
        api_key: str,
        api_secret: str,
        demo_trading: bool = DEMO_TRADING,
        default_type: str = DEFAULT_TYPE,
        exchange_id: str = DEFAULT_EXID,
        name: str | None = None,
    ):
        ex_class = getattr(ccxt, exchange_id)
        self.exchange = ex_class({"apiKey": api_key, "secret": api_secret, "enableRateLimit": True})
        self.name = name or getattr(self.exchange, "id", exchange_id)
        self.exchange.enable_demo_trading(bool(demo_trading))
        self.exchange.options["defaultType"] = default_type

        print(f"Loading markets ({self.name} | {'testnet' if demo_trading else 'live'})...")
        self.exchange.load_markets()
        self._force_hedge_mode()
        print("Ready.\n")

    # ---------- basic helpers ----------
    def symbol_for(self, base: str) -> str:
        return f"{base.strip().upper()}/{QUOTE}{CONTRACT_SUFFIX}"

    def get_balance_usdt(self) -> float:
        bal = self.exchange.fetch_balance()
        return float(bal["total"]["USDT"])

    def get_market_price(self, base: str) -> float:
        symbol = self.symbol_for(base)
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
            self.exchange.set_position_mode(True)  # dual-side
        except Exception:
            pass
        try:
            if hasattr(self.exchange, "fetch_position_mode"):
                info = self.exchange.fetch_position_mode()
                if not bool(info.get("hedged", True)):
                    try:
                        self.exchange.set_position_mode(True)
                    except Exception:
                        pass
        except Exception:
            pass

    @staticmethod
    def _position_idx_for_side(side: str) -> int:
        return 1 if side.lower() == "buy" else 2

    def _new_client_oid(self, group_key: str | None = None) -> str:
        ts = int(time.time() * 1000)
        # Keep the same logical group across exchanges if group_key is provided
        # Format: PREFIX-GROUP-ACCOUNT-TS  (clientOrderId)
        base = f"{ORDER_TAG}-{group_key}-{self.name}" if group_key else f"{ORDER_TAG}-{self.name}"
        return f"{base}-{ts}"

    # ---------- leverage ----------
    @inject
    def apply_leverage(
        self,
        config: TradeConfig = Provide[Container.trade_config],
        params: TradeParams = Provide[Container.trade_params],
    ):
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

    # ---------- orders (include clientOrderId) ----------
    @inject
    def market_order_with_stop(
        self,
        side: str,
        amount: float,
        group_key: str | None = None,
        config: TradeConfig = Provide[Container.trade_config],
        params: TradeParams = Provide[Container.trade_params],
    ):
        symbol = config.symbol
        sl_px = params.stop_loss_price
        amt = float(self.exchange.amount_to_precision(symbol, amount))
        sl = self.exchange.price_to_precision(symbol, sl_px)
        client_oid = self._new_client_oid(group_key)
        return self.exchange.create_order(
            symbol,
            "market",
            side,
            amt,
            None,
            {
                "clientOrderId": client_oid,
                "positionIdx": self._position_idx_for_side(side),
                "stopLoss": sl,
                "slTriggerBy": "LastPrice",
                "tpslMode": "Full",
            },
        )

    @inject
    def limit_order_with_stop(
        self,
        side: str,
        amount: float,
        group_key: str | None = None,
        config: TradeConfig = Provide[Container.trade_config],
        params: TradeParams = Provide[Container.trade_params],
    ):
        symbol = config.symbol
        entry = params.entry_price
        sl_px = params.stop_loss_price
        if entry is None:
            raise ValueError("entry_price must be provided for LIMIT orders.")
        amt = float(self.exchange.amount_to_precision(symbol, amount))
        px = self.exchange.price_to_precision(symbol, float(entry))
        sl = self.exchange.price_to_precision(symbol, sl_px)
        client_oid = self._new_client_oid(group_key)
        return self.exchange.create_order(
            symbol,
            "limit",
            side,
            amt,
            px,
            {
                "clientOrderId": client_oid,
                "postOnly": True,
                "positionIdx": self._position_idx_for_side(side),
                "stopLoss": sl,
                "slTriggerBy": "LastPrice",
                "tpslMode": "Full",
            },
        )

    # ---------- order management (cancel/close) ----------
    def fetch_open_orders(self, symbol: str | None = None) -> list[dict]:
        try:
            return self.exchange.fetch_open_orders(symbol)
        except Exception:
            return []

    def cancel_order_by_key(self, order_key: str, symbol: str | None = None) -> dict:
        """
        order_key can be an exchange order id OR a clientOrderId.
        We try to cancel by id first; if that fails, we search open orders and cancel matches by clientOrderId.
        """
        # Try direct id cancel (fast path)
        try:
            return {"ok": True, "resp": self.exchange.cancel_order(order_key, symbol)}
        except Exception:
            pass

        # Fallback: find by clientOrderId among open orders
        opens = self.fetch_open_orders(symbol)
        for o in opens:
            cid = (o.get("clientOrderId") or "").strip()
            oid = (o.get("id") or "").strip()
            if order_key == cid or order_key == oid:
                try:
                    return {"ok": True, "resp": self.exchange.cancel_order(oid or order_key, symbol)}
                except Exception as e:
                    return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "not found among open orders"}

    def cancel_all_ours(self, symbol: str | None = None) -> dict:
        """Cancel all open orders that carry our ORDER_TAG in clientOrderId."""
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
        """
        Cancel all open orders (ours + non-ours). Use exchange native 'cancel_all_orders' if present,
        else fall back to iterating open orders.
        """
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
        """
        Flatten positions using reduce-only market orders.
        In hedge mode, close long with sell (positionIdx=1) and short with buy (positionIdx=2).
        """
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
            if symbol and sym != symbol:
                continue
            contracts = abs(float(p.get("contracts") or p.get("contractSize") or p.get("amount") or 0))
            if contracts <= 0:
                continue
            side = (p.get("side") or "").lower()  # 'long' or 'short' in ccxt
            if side == "long":
                _reduce(sym, "sell", contracts, 1)  # close long
            elif side == "short":
                _reduce(sym, "buy", contracts, 2)   # close short

        return {"ok": len(errors) == 0, "closed": closed, "errors": errors}


class ExchangeClient:
    """The only object the calculator talks to. Manages one or many accounts internally."""
    def __init__(self):
        self._clients: list[SingleExchangeClient] = []
        if ACCOUNTS:
            for acc in ACCOUNTS:
                self._clients.append(
                    SingleExchangeClient(
                        api_key=acc["api_key"],
                        api_secret=acc["api_secret"],
                        demo_trading=bool(acc.get("demo", DEMO_TRADING)),
                        default_type=acc.get("default_type", DEFAULT_TYPE),
                        exchange_id=acc.get("exchange_id", DEFAULT_EXID),
                        name=acc.get("name"),
                    )
                )
        else:
            self._clients.append(
                SingleExchangeClient(
                    api_key=API_KEY,
                    api_secret=API_SECRET,
                    demo_trading=DEMO_TRADING,
                    default_type=DEFAULT_TYPE,
                    exchange_id=DEFAULT_EXID,
                    name="primary",
                )
            )
        self._display_index = DISPLAY_INDEX if DISPLAY_INDEX < len(self._clients) else 0

        required = (
            "get_balance_usdt",
            "get_market_price",
            "get_current_leverage",
            "market_order_with_stop",
            "limit_order_with_stop",
            "apply_leverage",
            "symbol_for",
            "fetch_open_orders",
            "cancel_order_by_key",
            "cancel_all_ours",
            "cancel_all_open_orders",
            "close_all_positions",
        )
        for c in self._clients:
            for attr in required:
                if not hasattr(c, attr):
                    raise AttributeError(f"{c.__class__.__name__} missing required method: {attr}")

    # ---------- primary proxies (for UI/preview) ----------
    @property
    def primary(self) -> SingleExchangeClient:
        return self._clients[self._display_index]

    def symbol_for(self, base: str) -> str:
        return self.primary.symbol_for(base)

    def get_balance_usdt(self) -> float:
        return self.primary.get_balance_usdt()

    def get_market_price(self, base: str) -> float:
        return self.primary.get_market_price(base)

    def get_current_leverage(self, symbol: str) -> float | None:
        return self.primary.get_current_leverage(symbol)

    def name(self) -> str:
        return self.primary.name

    def preview_primary_sizing(self, balance_usdt: float) -> dict:
        return calculate_position_sizing(balance_usdt)

    # ---------- trading (fan-out) ----------
    def submit_all(self, order_type: OrderType, side: str) -> list[dict]:
        group_key = str(int(time.time() * 1000))  # same logical group across exchanges
        results: list[dict] = []
        for c in self._clients:
            try:
                bal = c.get_balance_usdt()
                sizing = calculate_position_sizing(bal)
                amt = sizing["position_size"]
                r_usd = sizing["risk_usdt"]
                c.apply_leverage()
                if order_type == OrderType.MARKET:
                    resp = c.market_order_with_stop(side=side, amount=amt, group_key=group_key)
                else:
                    resp = c.limit_order_with_stop(side=side, amount=amt, group_key=group_key)
                results.append(
                    {"name": c.name, "ok": True, "id": resp.get("id", resp), "amount": amt, "risk_usd": r_usd}
                )
            except Exception as e:
                results.append({"name": c.name, "ok": False, "error": str(e)})
        return results

    # ---------- order management (across all accounts) ----------
    def cancel_specific_everywhere(self, order_key: str, symbol: str | None = None) -> list[dict]:
        """
        A) Cancel a specific order across all APIs by id or clientOrderId.
        """
        out = []
        for c in self._clients:
            res = c.cancel_order_by_key(order_key, symbol)
            out.append({"name": c.name, **res})
        return out

    def cancel_all_ours(self, symbol: str | None = None) -> list[dict]:
        """
        B) Cancel every order our software placed (matches ORDER_TAG).
        """
        out = []
        for c in self._clients:
            res = c.cancel_all_ours(symbol)
            out.append({"name": c.name, **res})
        return out

    def cancel_all_everywhere(self, symbol: str | None = None) -> list[dict]:
        """
        C) Cancel every open order on every API (ours + non-ours).
        """
        out = []
        for c in self._clients:
            res = c.cancel_all_open_orders(symbol)
            out.append({"name": c.name, **res})
        return out

    def close_all_positions(self, symbol: str | None = None) -> list[dict]:
        """
        Flatten positions everywhere (reduce-only market exits).
        """
        out = []
        for c in self._clients:
            res = c.close_all_positions(symbol)
            out.append({"name": c.name, **res})
        return out
