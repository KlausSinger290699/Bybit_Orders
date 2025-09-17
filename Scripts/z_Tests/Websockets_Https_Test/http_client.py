import time, random, requests

URL = "http://127.0.0.1:8765/div"
TF_CHOICES = ["1", "5", "15", "30"]

def make_event():
    side = random.choice(["bull", "bear"])
    tf = random.choice(TF_CHOICES)
    status = "?"
    start = int(time.time())
    end = start + int(tf) * 60
    return {
        "source": "test",
        "side": side,
        "status": status,
        "tf": tf,
        "start": start,
        "end": end,
    }

if __name__ == "__main__":
    print("✅ Connected (HTTP mode).")
    print("↩️  Press ENTER to send a random CVD event (bull/bear). Type 'q' + ENTER to quit.")
    while True:
        try:
            user = input()
        except (EOFError, KeyboardInterrupt):
            break
        if user.strip().lower() == "q":
            break

        e = make_event()
        r = requests.post(URL, json=e, timeout=5)
        if r.ok:
            print(f"📤 Sent: {e['side'].upper()} {e['tf']}m ({e['status']})")
            print(f"📨 Got reply: {r.json().get('message')}")
        else:
            print(f"❌ POST {URL} → {r.status_code}")
