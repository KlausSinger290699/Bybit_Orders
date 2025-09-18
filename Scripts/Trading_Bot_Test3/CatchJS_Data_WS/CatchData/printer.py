from typing import Optional
from . import utils

class Printer:
    def __init__(self):
        self._cur_seq: Optional[int] = None
        self._buf: list[dict] = []

    def _flush(self):
        if not self._buf or self._cur_seq is None:
            return

        def l1_time(ev: dict):
            l1, _ = utils.extract_L1_L2(ev)
            t = l1.get("time")
            return t if isinstance(t, (int, float)) else float("inf")

        batch = sorted(self._buf, key=l1_time)
        self._buf.clear()

        tf_label = batch[-1].get("tf_label") or utils.fmt_tf(batch[-1].get("tf_sec"))
        top_bar, bottom_bar = self._seq_bars(self._cur_seq, tf_label)
        print("\n" + top_bar)

        for ev in batch:
            side = ev.get("side", "?")
            side_icon = "🟢" if side == "bull" else "🔴" if side == "bear" else "⚪"
            status_icon = ev.get("status", "?")
            l1, l2 = utils.extract_L1_L2(ev)
            l1p = utils.fmt_price(l1.get("price"))
            l2p = utils.fmt_price(l2.get("price"))
            print(f"{status_icon} {side_icon} | {l1p}-{l2p}")

        print(bottom_bar)
        self._cur_seq = None

    def add_event(self, ev: dict):
        seq = ev.get("sequence")
        if self._cur_seq is None:
            self._cur_seq = seq
        elif seq != self._cur_seq:
            self._flush()
            self._cur_seq = seq
        self._buf.append(ev)

    def flush_now(self):
        self._flush()

    @staticmethod
    def _seq_bars(seq_no: int, tf_label: str):
        title = f"📌 Sequence #{seq_no} — {tf_label} "
        inner_line = "━━ " + title + "━" * max(0, 58 - len(title))
        return f"┏{inner_line}┓", f"┗{'━' * len(inner_line)}┛"
