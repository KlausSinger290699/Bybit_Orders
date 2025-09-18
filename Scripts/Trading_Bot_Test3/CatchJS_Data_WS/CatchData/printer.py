from . import utils

EVENTS_PER_SEQUENCE = 4  # ← adjust to your stream

class SequencePrinter:
    """Top → lines → bottom. Close on Nth line OR explicitly when told."""
    def __init__(self, per_sequence: int = EVENTS_PER_SEQUENCE):
        self.per_sequence = per_sequence
        self.current_seq_id = None
        self.lines_in_current = 0
        self._open = False
        self._bottom_bar = None

    def start(self, seq_id: int, tf_label: str):
        """Start a new sequence (header now). Assumes caller closed previous."""
        top, bottom = utils.seq_bars(seq_id, tf_label)
        print("\n" + top)
        self.current_seq_id = seq_id
        self._bottom_bar = bottom
        self.lines_in_current = 0
        self._open = True

    def add(self, event: dict):
        """Print one line; if Nth line, print footer now and reset."""
        if not self._open:
            # Defensive: auto-start with this event
            seq_id = event.get("sequence")
            tf_label = utils._choose_tf_label([event])
            self.start(seq_id, tf_label)

        side = event.get("side", "?")
        side_icon = "🟢" if side == "bull" else "🔴" if side == "bear" else "⚪"
        status_icon = event.get("status", "?")

        l1, l2 = utils.extract_L1_L2(event)
        l1_price = utils.fmt_price(l1.get("price"))
        l2_price = utils.fmt_price(l2.get("price"))

        print(f"{status_icon} {side_icon} | {l1_price}-{l2_price}")

        self.lines_in_current += 1
        if self.lines_in_current >= self.per_sequence:
            self._print_footer_and_reset()

    def end_if_open(self):
        """Explicitly close the current sequence (used on seq change / shutdown)."""
        if self._open:
            self._print_footer_and_reset()

    # --- internals ---
    def _print_footer_and_reset(self):
        if self._open and self._bottom_bar:
            print(self._bottom_bar)
        self._open = False
        self._bottom_bar = None
        self.current_seq_id = None
        self.lines_in_current = 0
