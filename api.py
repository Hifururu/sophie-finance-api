# api.py
import os
from flask import Flask, jsonify, request

app = Flask(__name__)

# -------- Health & Home --------
@app.get("/health")
def health():
    return jsonify(ok=True), 200

@app.get("/")
def home():
    return "Sophie API viva ✅", 200


# -------- Seguridad simple (Bearer) --------
SECRET = os.environ.get("SECRET_TOKEN", "")

def check_auth(req):
    auth = req.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    token = auth.split(" ", 1)[1]
    return token == SECRET


# -------- Endpoints de Finanzas (dummy, sin BD) --------
@app.post("/api/tx")
def add_tx():
    # Autenticación
    if not check_auth(request):
        return jsonify(error="unauthorized"), 401

    data = request.get_json(silent=True) or {}
    required = ["user_id", "date", "type", "category", "concept", "amount_clp", "source"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify(error=f"missing fields: {', '.join(missing)}"), 400

    if data["type"] not in ("income", "expense"):
        return jsonify(error="type must be income|expense"), 400

    # Por ahora no guardamos en BD; solo devolvemos 'ok' y lo que llegó
    return jsonify(status="ok", stored=False, echo=data), 200


@app.get("/api/summary")
def summary():
    # Dummy de resumen (cuando conectemos BD esto devolverá datos reales)
    if not check_auth(request):
        return jsonify(error="unauthorized"), 401
    month = request.args.get("month", "YYYY-MM")
    return jsonify(
        user_id="felipe",
        month=month,
        income_clp=0,
        expense_clp=0,
        balance_clp=0,
        by_category={}
    ), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
# api.py
import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.get("/health")
def health():
    return jsonify(ok=True), 200

@app.get("/")
def home():
    return "Sophie API viva ✅", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
