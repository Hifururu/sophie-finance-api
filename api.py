# api.py
import os
from datetime import datetime, date
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# -------------------- Config DB --------------------
DB_URL = os.environ.get("DATABASE_URL")
if not DB_URL:
    # Si quieres que arranque sin BD, comenta este raise (pero no guardará nada).
    raise RuntimeError("DATABASE_URL env var is required")

app.config["SQLALCHEMY_DATABASE_URI"] = DB_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class Transaction(db.Model):
    __tablename__ = "transactions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(64), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    type = db.Column(db.String(10), nullable=False)  # "income" | "expense"
    category = db.Column(db.String(64), nullable=False)
    concept = db.Column(db.String(255), nullable=False)
    amount_clp = db.Column(db.Integer, nullable=False)  # CLP sin decimales
    source = db.Column(db.String(32), nullable=False)   # lawrence|haru|sophie
    idempotency_key = db.Column(db.String(64), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# -------------------- Seguridad simple --------------------
SECRET = os.environ.get("SECRET_TOKEN", "")

def check_auth(req):
    """Bearer <SECRET_TOKEN>"""
    auth = req.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    token = auth.split(" ", 1)[1]
    return token == SECRET


# -------------------- Health & Home --------------------
@app.get("/health")
def health():
    return jsonify(ok=True), 200

@app.get("/")
def home():
    return "Sophie API viva ✅ v2", 200


# -------------------- Finanzas --------------------
@app.post("/api/tx")
def add_tx():
    if not check_auth(request):
        return jsonify(error="unauthorized"), 401

    data = request.get_json(silent=True) or {}
    required = ["user_id", "date", "type", "category", "concept", "amount_clp", "source"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify(error=f"missing fields: {', '.join(missing)}"), 400

    if data["type"] not in ("income", "expense"):
        return jsonify(error="type must be income|expense"), 400

    # Idempotencia (evita duplicados si ya se procesó esa clave)
    idem = data.get("idempotency_key")
    if idem:
        exists = Transaction.query.filter_by(idempotency_key=idem).first()
        if exists:
            return jsonify(status="duplicate_ignored", stored=True, id=exists.id), 200

    try:
        tx = Transaction(
            user_id=data["user_id"],
            date=datetime.strptime(data["date"], "%Y-%m-%d").date(),
            type=data["type"],
            category=str(data["category"]).lower(),
            concept=data["concept"],
            amount_clp=int(data["amount_clp"]),
            source=str(data["source"]).lower(),
            idempotency_key=idem
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
        y, m = month.split("-")
        y, m = int(y), int(m)
        start = date(y, m, 1)
        end = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
        q = q.filter(Transaction.date >= start, Transaction.date < end)

    rows = q.all()
    income = sum(r.amount_clp for r in rows if r.type == "income")
    expense = sum(r.amount_clp for r in rows if r.type == "expense")
    by_cat = {}
    for r in rows:
        # Para categorías: sumamos gastos como positivo (lo que “sale”)
        # Si prefieres ingresos positivos y gastos negativos, cambia el signo aquí.
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
        count=len(rows)
    ), 200


# -------------------- Diagnóstico --------------------
@app.get("/__diag")
def diag():
    try:
        has_db_url = bool(os.environ.get("DATABASE_URL"))
        count = Transaction.query.count()
        return jsonify(version="pg-v1", has_db_url=has_db_url, rows_in_db=count), 200
    except Exception as e:
        return jsonify(version="pg-v1", error=str(e)), 500


# -------------------- Init & Run --------------------
with app.app_context():
    # Crea las tablas si no existen
    db.create_all()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
