# log_uniform.py
class UniformLogger:
    def __init__(self, role: str):
        self.role = role.upper()

    def _fmt_reason(self, code, reason):
        r = (reason or "").strip()
        code_str = code if code is not None else "?"
        r_str = r if r else "<none>"
        return f"code={code_str} reason={r_str}"

    def starting(self):        print(f"🚀 [{self.role}] Starting ...")
    def waiting(self):         print(f"⏳ [{self.role}] Waiting ...")
    def connected(self):       print(f"✅ [{self.role}] Connected.")
    def ready(self):           print(f"🟢 [{self.role}] Ready.")
    def prompt(self):          print("↩️  Press ENTER to send a random CVD event. Type 'q' + ENTER to quit.", end="", flush=True)
    def disconnected(self, code, reason): print(f"🔌 [{self.role}] Disconnected: {self._fmt_reason(code, reason)}")
    def closing_by_user(self): print(f"👋 [{self.role}] Closing by user request.")
    def recv_raw(self, msg):   print(f"📥 [{self.role}] Received (raw): {msg}")
    def recv_summary(self, side, tf, status): print(f"📥 [{self.role}] Received (summary): {side} {tf}m ({status})")
    def sent_json(self, payload): print(f"📤 [{self.role}] Sent back (json): {payload}\n")
    def sent_summary(self, side, tf, status): print(f"📤 [{self.role}] Sent (summary): {side.upper()} {tf}m ({status})")
    def sent_wire(self, wire): print(f"📤 [{self.role}] Sent (json)   : {wire}")
    def got_reply(self, reply): print(f"📨 [{self.role}] Got reply (raw): {reply}\n")
    def stopped_by_user(self): print(f"\n🟥 [{self.role}] Stopped by user.")
