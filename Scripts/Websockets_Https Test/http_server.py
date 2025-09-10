from flask import Flask, request, jsonify

app = Flask(__name__)

@app.post("/div")
def div():
    data = request.get_json(force=True, silent=True) or {}
    side = (data.get("side") or "?").upper()
    tf = data.get("tf") or "?"
    status = data.get("status") or "?"
    print(f"📥 HTTP Server received: {side} {tf}m ({status})")
    # Reply with a clear JSON message (mirrors WS server reply style)
    return jsonify(message=f"Server received {side} {tf}m ({status})"), 200

if __name__ == "__main__":
    print("🔊 HTTP server listening on http://127.0.0.1:8765/div")
    app.run(host="127.0.0.1", port=8765)
