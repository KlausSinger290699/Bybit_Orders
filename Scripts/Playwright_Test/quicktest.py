from flask import Flask, request

app = Flask(__name__)

@app.post("/log")
def log():
    data = request.get_json(force=True, silent=True)
    print("[PY RECEIVED]", data)
    return "ok"

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
