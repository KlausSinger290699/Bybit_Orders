import time, requests

URL = "http://127.0.0.1:8765/div"

payloads = [
    {"source": "test", "side": "bear", "status": "?", "tf": "15",
     "start": int(time.time()), "end": int(time.time()) + 900},
    {"source": "test", "side": "bull", "status": "?", "tf": "5",
     "start": int(time.time()), "end": int(time.time()) + 300},
]

for p in payloads:
    r = requests.post(URL, json=p, timeout=5)
    if r.ok:
        print(f"📤 Sent: {p['side'].upper()} {p['tf']}m ({p['status']})")
        print(f"📨 Got reply: {r.json().get('message')}")
    else:
        print(f"❌ POST {URL} → {r.status_code}")
