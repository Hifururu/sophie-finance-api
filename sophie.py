# sophie.py
from fastapi import FastAPI, Request
from pydantic import BaseModel
import os, re

app = FastAPI(
    title="Sophie API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

BANNER = "🚀 Sophie API viva ✅ v5"

@app.get("/")
def root():
    return BANNER

@app.get("/__diag")
def diag():
    db_url = os.getenv("DATABASE_URL", "")
    has_db_url = bool(db_url)
    rows_in_db = 0
    return {"has_db_url": has_db_url, "rows_in_db": rows_in_db, "version": "pg-v1"}

@app.get("/__routes")
def list_routes(request: Request):
    routes = []
    for r in request.app.routes:
        path = getattr(r, "path", None)
        methods = list(getattr(r, "methods", []) or [])
        if path:
            routes.append({"path": path, "methods": methods})
    routes.sort(key=lambda x: x["path"])
    return routes

class MensajeIn(BaseModel):
    mensaje: str

@app.post("/procesar")
def procesar(payload: MensajeIn):
    text = payload.mensaje.lower()
    acciones = []
    monto = None
    m = re.search(r"(?:\$|clp\s*)?(\d{1,3}(?:[.,]\d{3})*|\d+)", text)
    if m:
        raw = m.group(1)
        try:
            monto = int(re.sub(r"[.,]", "", raw))
        except ValueError:
            monto = None
    if any(k in text for k in ["combo", "mcdonald", "cuarto de libra", "burger", "hamburguesa"]) or monto:
        acciones.append({
            "agente": "Lawrence",
            "tipo": "gasto",
            "categoria": "comida",
            "concepto": "combo cuarto de libra" if ("cuarto" in text or "combo" in text) else "comida",
            "monto_clp": monto or 0
        })
    if ("repasar" in text or "estudiar" in text) and ("kanji" in text or "kanjis" in text):
        kanjis = re.findall(r"[一-龯々〆ヵヶ]", text)
        acciones.append({
            "agente": "Haru",
            "tipo": "estudio",
            "objetivo": "Repasar kanjis",
            "kanjis": kanjis[:20]
        })
    if not acciones:
        acciones.append({"agente": "Sophie", "tipo": "nota", "detalle": "No se detectaron acciones"})
    return {"ok": True, "acciones": acciones}


