# sophie_api.py
import os
from datetime import datetime, date
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

# ---- Integración con Sophie -------------------------------------------------
# Debe existir un archivo sophie.py en la raíz con:
#   def sophie(mensaje: str) -> str
from sophie import sophie as sophie_fn

# ---- App & Config ------------------------------------------------------------
app = Flask(__name__)

DB_URL = os.environ.get("DATABASE_URL")
if not DB_URL:
    raise RuntimeError(
        "DATABASE_URL env var is required "
        "(e.g. postgresql+psycopg2://user:pass@host:5432/db)"
    )

app.config["SQLALCHEMY_DATABASE_URI"] = DB_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ---- Modelo ------------------------------------------------------------------
class Transaction(db.Model):
    __tablename__ = "transactions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(64), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    type = db.Column(db.String(10), nullable=False)               # income | expense
    category = db.Column(db.String(64), nullable=False)
    concept = db.Column(db.String(255), nullable=False)
    amount_clp = db.Column(db.Integer, nullable=False)
    source = db.Column(db.String(32), nullable=False)
    idempotency_key = db.Column(db.String(64), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ---- Auth simple (Bearer) ----------------------------------------------------
SECRET = os.environ.get("SECRET_TOKEN", "")

def check_auth(req) -> bool:
    auth = req.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    token = auth.split(" ", 1)[1]
    return token == SECRET

# ---- Salud & Home ------------------------------------------------------------
@app.get("/health")
def health():
    return jsonify(ok=True), 200

@app.get("/")
def home():
    return "🚀 Sophie API viva ✅ v5", 200

# ---- Finanzas ----------------------------------------------------------------
@app.post("/api/tx")
def add_tx():
    if not check_auth(request):
        return jsonify(error="unauthorized"), 401

    data = request.get_json(silent=True) or {}
    required = ["user_id", "date", "type", "category", "concept", "amount_clp", "source"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify(error=f"missing fields: {', '.join(missing)}"), 400

    ttype = str(data["type"]).lower()
    if ttype not in ("income", "expense"):
        return jsonify(error="type must be income|expense"), 400

    idem = data.get("idempotency_key")
    if idem:
        exists = Transaction.query.filter_by(idempotency_key=idem).first()
        if exists:
            return jsonify(status="duplicate_ignored", stored=True, id=exists.id), 200

    try:
        tx = Transaction(
            user_id=str(data["user_id"]),
            date=datetime.strptime(str(data["date"]), "%Y-%m-%d").date(),
            type=ttype,
            category=str(data["category"]).lower(),
            concept=str(data["concept"]),
            amount_clp=int(data["amount_clp"]),
            source=str(data["source"]).lower(),
            idempotency_key=str(idem) if idem else None,
        )
        db.session.add(tx)
        db.session.commit()
        return jsonify(status="ok", stored=True, id=tx.id), 200
    except Exception as e:
        db.session.rollback()
        return jsonify(error=str(e)), 500

@app.get("/api/summary")
def summary():
    if not check_auth(request):
        return jsonify(error="unauthorized"), 401

    user_id = request.args.get("user_id", "felipe")
    month = request.args.get("month")  # YYYY-MM opcional

    q = Transaction.query.filter_by(user_id=user_id)
    if month:
        y, m = map(int, month.split("-"))
        start = date(y, m, 1)
        end = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
        q = q.filter(Transaction.date >= start, Transaction.date < end)

    rows = q.all()
    income = sum(r.amount_clp for r in rows if r.type == "income")
    expense = sum(r.amount_clp for r in rows if r.type == "expense")

    by_cat: dict[str, int] = {}
    for r in rows:
        if r.type == "expense":
            by_cat[r.category] = by_cat.get(r.category, 0) + r.amount_clp
        else:
            by_cat[r.category] = by_cat.get(r.category, 0) - r.amount_clp

    return jsonify(
        user_id=user_id,
        month=month,
        income_clp=income,
        expense_clp=expense,
        balance_clp=income - expense,
        by_category=by_cat,
        count=len(rows),
    ), 200

# ---- Diagnóstico -------------------------------------------------------------
@app.get("/__routes")
def routes():
    return jsonify(sorted([f"{r.rule} [{','.join(sorted(r.methods))}]" for r in app.url_map.iter_rules()]))

@app.get("/__diag")
def diag():
    try:
        has_db_url = bool(os.environ.get("DATABASE_URL"))
        count = Transaction.query.count()
        return jsonify(version="pg-v1", has_db_url=has_db_url, rows_in_db=count), 200
    except Exception as e:
        return jsonify(version="pg-v1", error=str(e)), 500

# ---- Sophie (procesador de mensajes) -----------------------------------------
@app.post("/procesar")
def procesar():
    """
    Recibe JSON: { "mensaje": "texto libre" }
    Llama sophie.sophie(mensaje) y devuelve texto.
    Respuesta: { ok: true, salida: "<texto>" }
    """
    data = request.get_json(silent=True) or {}
    mensaje = str(data.get("mensaje", "")).strip()
    if not mensaje:
        return jsonify(error="mensaje requerido"), 400
    try:
        salida = sophie_fn(mensaje)
        return jsonify(ok=True, salida=salida), 200
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

# ---- Init tablas al arrancar -------------------------------------------------
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(">>> 🚀 Running Sophie API v5 with __routes, __diag, /procesar")
    app.run(host="0.0.0.0", port=port)
