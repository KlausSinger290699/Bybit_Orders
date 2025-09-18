import atexit
from . import utils

EVENTS_PER_SEQUENCE = 4  # adjust to your stream


class SequencePrinter:
    """Print: header → N lines → footer. One stream only (processed)."""
    def __init__(self, per_sequence: int = EVENTS_PER_SEQUENCE):
        self.per_sequence = per_sequence
        self.seq_id = None
        self.footer = ""
        self.count = 0
        atexit.register(self.flush)

    def print_event(self, event: dict):
        seq = event.get("sequence")
        if seq != self.seq_id:
            # start fresh sequence
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

    def flush(self):
        if self.footer:
            print(self.footer)
        self.seq_id = None
        self.footer = ""
        self.count = 0
