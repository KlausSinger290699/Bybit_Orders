# printer.py
import atexit
from typing import Any, Iterable, Optional
from . import utils


def _infer_label(events: Iterable[dict]) -> Optional[str]:
    """Return 'Bybit' if any event has H1, else infer from 'source', else None."""
    events = list(events)
    if not events:
        return None
    if any(isinstance(ev.get("H1"), dict) and "price" in ev["H1"] for ev in events):
        return "Bybit"
    src = str((events[0] or {}).get("source") or "").lower()
    if "aggr" in src:
        return "Aggr"
    if "bybit" in src:
        return "Bybit"
    return None


class _SeqPrinter:
    """Pretty sequence printer: header → lines → footer."""

    def __init__(self) -> None:
        self._seq_id: Optional[int] = None
        self._footer: str = ""
        atexit.register(self._flush)

    def _line_for_event(self, ev: dict) -> str:
        side = ev.get("side", "?")
        icon = "🟢" if side == "bull" else "🔴" if side == "bear" else "⚪"
        status = ev.get("status", "?")
        l1, l2 = utils.extract_L1_L2(ev)
        base = f"{status} {icon} | {utils.fmt_price(l1.get('price'))}-{utils.fmt_price(l2.get('price'))}"
        h1 = ev.get("H1")
        if isinstance(h1, dict) and "price" in h1:
            base += f" | H1 {utils.fmt_price(h1.get('price'))}"
        return base

    def _open_box(self, events: list[dict]) -> None:
        seq = events[0].get("sequence")
        tf = utils.choose_tf_label(events)
        label = _infer_label(events)
        top, bottom = utils.seq_bars(seq, tf, label)
        print("\n" + top)
        self._seq_id = seq
        self._footer = bottom

    def _close_box(self) -> None:
        if self._footer:
            print(self._footer)
        self._seq_id = None
        self._footer = ""

    def print_event(self, data: Any) -> None:
        """Accept a single dict or a list[dict] and print properly."""
        if isinstance(data, list):
            if not data:
                return
            self._open_box(data)
            for ev in data:
                print(self._line_for_event(ev))
            self._close_box()
        else:
            ev = data
            seq = ev.get("sequence")
            if seq != self._seq_id:
                self._open_box([ev])
            print(self._line_for_event(ev))

    def _flush(self) -> None:
        self._close_box()


_prn = _SeqPrinter()

def print_sequence(data: Any) -> None:
    """Public API: print a single event or a full block (list[dict])."""
    _prn.print_event(data)
