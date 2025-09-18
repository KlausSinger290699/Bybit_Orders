import atexit
from . import utils

EVENTS_PER_SEQUENCE = 4  # adjust to your stream

class _SeqPrinter:
    def __init__(self, per_sequence: int = EVENTS_PER_SEQUENCE):
        self.per_sequence = per_sequence
        self.seq_id = None
        self.footer = ""
        self.count = 0
        atexit.register(self._flush)

    def _print_one(self, event: dict):
        """Existing single-event path (unchanged)."""
        seq = event.get("sequence")
        if seq != self.seq_id:
            tf = utils.choose_tf_label([event])
            top, self.footer = utils.seq_bars(seq, tf)
            print("\n" + top)
            self.seq_id = seq
            self.count = 0

        side = event.get("side", "?")
        icon = "🟢" if side == "bull" else "🔴" if side == "bear" else "⚪"
        status = event.get("status", "?")
        l1, l2 = utils.extract_L1_L2(event)
        print(f"{status} {icon} | {utils.fmt_price(l1.get('price'))}-{utils.fmt_price(l2.get('price'))}")

        self.count += 1
        if self.count >= self.per_sequence:
            print(self.footer)
            self.seq_id = None
            self.footer = ""
            self.count = 0

    def _print_batch(self, events: list[dict]):
        """Print a full block at once: header → lines → footer."""
        if not events:
            return
        seq = events[0].get("sequence")
        tf = utils.choose_tf_label(events)
        top, bottom = utils.seq_bars(seq, tf)
        print("\n" + top)
        for ev in events[:self.per_sequence]:
            side = ev.get("side", "?")
            icon = "🟢" if side == "bull" else "🔴" if side == "bear" else "⚪"
            status = ev.get("status", "?")
            l1, l2 = utils.extract_L1_L2(ev)
            print(f"{status} {icon} | {utils.fmt_price(l1.get('price'))}-{utils.fmt_price(l2.get('price'))}")
        print(bottom)
        # reset internal rolling state
        self.seq_id = None
        self.footer = ""
        self.count = 0

    def print_event(self, data):
        """Accept either a single dict or a list[dict] and print properly."""
        if isinstance(data, list):
            self._print_batch(data)
        else:
            self._print_one(data)

    def _flush(self):
        if self.footer:
            print(self.footer)
        self.seq_id = None
        self.footer = ""
        self.count = 0

# module-level singleton to preserve state
_prn = _SeqPrinter()

def print_sequence(data):
    _prn.print_event(data)
