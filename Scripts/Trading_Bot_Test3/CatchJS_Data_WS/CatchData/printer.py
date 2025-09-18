from . import utils

EVENTS_PER_SEQUENCE = 4  # adjust to your stream


class SequencePrinter:
    """Print: header → N lines → footer. Never defer footer to next sequence."""
    def __init__(self, per_sequence: int = EVENTS_PER_SEQUENCE):
        self.per_sequence = per_sequence
        self.current_seq_id = None
        self._open = False
        self._bottom = None
        self._count = 0

    def start(self, seq_id: int, tf_label: str):
        """Start a new sequence (prints header)."""
        top, bottom = utils.seq_bars(seq_id, tf_label)
        print("\n" + top)
        self.current_seq_id = seq_id
        self._bottom = bottom
        self._count = 0
        self._open = True

    def add(self, event: dict):
        """Print one line; if it was the Nth, print footer now."""
        if not self._open:
            # Defensive: auto-start using this event
            self.start(event.get("sequence"), utils.choose_tf_label([event]))

        side = event.get("side", "?")
        side_icon = "🟢" if side == "bull" else "🔴" if side == "bear" else "⚪"
        status_icon = event.get("status", "?")

        l1, l2 = utils.extract_L1_L2(event)
        print(f"{status_icon} {side_icon} | {utils.fmt_price(l1.get('price'))}-{utils.fmt_price(l2.get('price'))}")

        self._count += 1
        if self._count >= self.per_sequence:
            self._print_footer_and_reset()

    def end_if_open(self):
        """Close current block (used on seq change or shutdown)."""
        if self._open:
            self._print_footer_and_reset()

    # --- internal ---
    def _print_footer_and_reset(self):
        if self._bottom:
            print(self._bottom)
        self._open = False
        self._bottom = None
        self.current_seq_id = None
        self._count = 0
