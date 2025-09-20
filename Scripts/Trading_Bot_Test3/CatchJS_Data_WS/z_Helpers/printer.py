# printer.py
import atexit
from . import utils

class _SeqPrinter:
    def __init__(self ):
        self.seq_id = None
        self.footer = ""
        self.count = 0
        atexit.register(self._flush)

    def _line_for_event(self, ev: dict) -> str:
        side = ev.get("side", "?")
        icon = "🟢" if side == "bull" else "🔴" if side == "bear" else "⚪"
        status = ev.get("status", "?")
        l1, l2 = utils.extract_L1_L2(ev)
        base = f"{status} {icon} | {utils.fmt_price(l1.get('price'))}-{utils.fmt_price(l2.get('price'))}"
        # Append H1 if present (processed Bybit block will have it)
        h1 = ev.get("H1")
        if isinstance(h1, dict) and "price" in h1:
            base += f" | H1 {utils.fmt_price(h1.get('price'))}"
        return base

    def _print_one(self, event: dict, tag: str | None = None):
        """Existing single-event path, with tagged headers and optional H1."""
        seq = event.get("sequence")
        if seq != self.seq_id:
            tf = utils.choose_tf_label([event])
            top, self.footer = utils.seq_bars(seq, tf, tag)
            print("\n" + top)
            self.seq_id = seq
            self.count = 0

        print(self._line_for_event(event))

        self.count += 1
        if self.count >= self.per_sequence:
            print(self.footer)
            self.seq_id = None
            self.footer = ""
            self.count = 0

    def _print_batch(self, events: list[dict], tag: str | None = None):
        if not events:
            return
        seq = events[0].get("sequence")
        tf = utils.choose_tf_label(events)
        top, bottom = utils.seq_bars(seq, tf, tag)
        print("\n" + top)
        for ev in events:  # ← no slicing; print all events in the block
            print(self._line_for_event(ev))
        print(bottom)
        self.seq_id = None
        self.footer = ""
        self.count = 0

    def print_event(self, data, tag: str | None = None):
        """Accept either a single dict or a list[dict] and print properly."""
        if isinstance(data, list):
            self._print_batch(data, tag=tag)
        else:
            self._print_one(data, tag=tag)

    def _flush(self):
        if self.footer:
            print(self.footer)
        self.seq_id = None
        self.footer = ""
        self.count = 0

# module-level singleton to preserve state
_prn = _SeqPrinter()

def print_sequence(data, tag: str | None = None):
    _prn.print_event(data, tag=tag)
