import os
import re
import csv
from pathlib import Path
from datetime import datetime, timedelta
from dateutil import tz
from openai import OpenAI

# ====== Configuración ======
API_KEY = os.getenv("OPENROUTER_API_KEY")
if not API_KEY:
    raise RuntimeError("❌ Falta OPENROUTER_API_KEY. En PowerShell: setx OPENROUTER_API_KEY \"sk-or-v1-...\" y abre una nueva terminal.")

client = OpenAI(api_key=API_KEY, base_url="https://openrouter.ai/api/v1")
TZ = tz.gettz("America/Santiago")

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
GASTOS_CSV = DATA_DIR / "gastos.csv"

# ====== Utilidades ======
def normaliza_fecha_relativa(texto: str) -> str:
    base = datetime.now(TZ).date()
    s = texto.lower()
    if "hoy" in s:
        return base.isoformat()
    if "pasado mañana" in s or "pasado manana" in s:
        return (base + timedelta(days=2)).isoformat()
    if "mañana" in s or "manana" in s:
        return (base + timedelta(days=1)).isoformat()
    return ""  # no hay fecha

def es_gasto(msg: str) -> bool:
    PAL = ["combo","comprar","pagar","gasto","precio","mcdonald","almuerzo","supermercado","transporte","cuarto de libra","snack","netflix"]
    m = msg.lower()
    return any(p in m for p in PAL)

def es_estudio(msg: str) -> bool:
    PAL = ["kanji","kanjis","japonés","japones","estudiar","repasar","hiragana","katakana"]
    m = msg.lower()
    return any(p in m for p in PAL)

def extrae_monto_clp(msg: str) -> int:
    """
    Busca números como 5.000, 12000, $9.990, $ 12.000 y devuelve entero.
    Si no encuentra, 0.
    """
    m = re.search(r"\$?\s*([\d\.]{3,})", msg)
    if not m:
        return 0
    try:
        return int(m.group(1).replace(".", ""))
    except:
        return 0

# ====== Formatos súper simples ======
# Lawrence debe responder EXACTAMENTE 5 líneas, en este formato:
# FECHA=YYYY-MM-DD o FECHA=no especificada
# CONCEPTO=...
# CATEGORIA=comida|transporte|ocio|hogar|estudios|otros
# MONTO_CLP=12345 (entero, sin decimales)
# TIPO=futuro
LAWRENCE_SYS = (
    "Eres Lawrence, asistente financiero de Felipe en Chile.\n"
    "Devuelve EXACTAMENTE 5 líneas en formato CLAVE=VALOR, sin texto extra y sin comillas:\n"
    "FECHA=YYYY-MM-DD (o FECHA=no especificada)\n"
    "CONCEPTO=texto corto\n"
    "CATEGORIA=comida|transporte|ocio|hogar|estudios|otros\n"
    "MONTO_CLP=entero (CLP sin decimales)\n"
    "TIPO=futuro\n"
    "Si menciona McDonald's/combos, usa CATEGORIA=comida.\n"
    "Si es gasto de japonés/kanji/libro japonés, usa CATEGORIA=estudios.\n"
    "Nunca uses decimales; CLP siempre entero.\n"
)

# Haru debe responder EXACTAMENTE 4 líneas, en este formato:
# FECHA=YYYY-MM-DD o FECHA=no especificada
# OBJETIVO=...
# KANJIS=kanji1,kanji2,kanji3 (3 a 5 kanjis)
# DURACION_MIN=25 (entero)
HARU_SYS = (
    "Eres Sensei-Haru. Prepara tarea N5. Devuelve EXACTAMENTE 4 líneas CLAVE=VALOR, sin texto extra:\n"
    "FECHA=YYYY-MM-DD (o FECHA=no especificada)\n"
    "OBJETIVO=texto corto\n"
    "KANJIS=lista separada por comas (3 a 5 kanjis)\n"
    "DURACION_MIN=entero (minutos)\n"
)

def pedir_lawrence(mensaje: str, fecha_iso: str) -> dict:
    monto_heur = extrae_monto_clp(mensaje)
    user = f"Mensaje: {mensaje}\nFecha: {fecha_iso or 'no especificada'}\nMontoDetectadoHeuristica: {monto_heur}"
    r = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[{"role":"system","content":LAWRENCE_SYS},{"role":"user","content":user}],
        temperature=0.2
    )
    texto = (r.choices[0].message.content or "").strip()
    # Parseo súper simple: 5 líneas CLAVE=VALOR
    datos = {"FECHA":"no especificada","CONCEPTO":"", "CATEGORIA":"otros","MONTO_CLP":"0","TIPO":"futuro"}
    for linea in texto.splitlines():
        if "=" in linea:
            k,v = linea.split("=",1)
            datos[k.strip().upper()] = v.strip()
    # Normaliza monto a entero
    try:
        datos["MONTO_CLP"] = str(int(re.sub(r"[^\d]","",datos.get("MONTO_CLP","0")) or "0"))
    except:
        datos["MONTO_CLP"] = "0"
    return datos

def pedir_haru(mensaje: str, fecha_iso: str) -> dict:
    user = f"Mensaje: {mensaje}\nFecha de estudio: {fecha_iso or 'no especificada'}"
    r = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[{"role":"system","content":HARU_SYS},{"role":"user","content":user}],
        temperature=0.2
    )
    texto = (r.choices[0].message.content or "").strip()
    # Parseo 4 líneas CLAVE=VALOR
    datos = {"FECHA":"no especificada","OBJETIVO":"", "KANJIS":"", "DURACION_MIN":"25"}
    for linea in texto.splitlines():
        if "=" in linea:
            k,v = linea.split("=",1)
            datos[k.strip().upper()] = v.strip()
    return datos

def asegurar_csv():
    if not GASTOS_CSV.exists():
        with GASTOS_CSV.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["fecha","concepto","categoria","monto_clp","tipo"])

def guardar_gasto(datos: dict):
    asegurar_csv()
    fila = [
        datos.get("FECHA",""),
        datos.get("CONCEPTO",""),
        datos.get("CATEGORIA","otros"),
        datos.get("MONTO_CLP","0"),
        datos.get("TIPO","futuro"),
    ]
    with GASTOS_CSV.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(fila)

def guardar_plan_kanji(datos: dict):
    fecha = datos.get("FECHA","sin-fecha")
    ruta = DATA_DIR / f"plan_kanji-{fecha}.txt"
    contenido = [
        f"Fecha: {fecha}",
        f"Objetivo: {datos.get('OBJETIVO','')}",
        f"Kanjis: {datos.get('KANJIS','')}",
        f"Duración (min): {datos.get('DURACION_MIN','25')}",
    ]
    ruta.write_text("\n".join(contenido), encoding="utf-8")

def sophie(mensaje: str) -> str:
    fecha = normaliza_fecha_relativa(mensaje)
    salidas = []

    if es_gasto(mensaje):
        l = pedir_lawrence(mensaje, fecha)
        guardar_gasto(l)
        salidas.append(f"💰 Lawrence → FECHA={l['FECHA']} | CONCEPTO={l['CONCEPTO']} | CATEGORIA={l['CATEGORIA']} | MONTO_CLP={l['MONTO_CLP']} | TIPO={l['TIPO']}")

    if es_estudio(mensaje):
        h = pedir_haru(mensaje, fecha)
        guardar_plan_kanji(h)
        salidas.append(f"📖 Haru → FECHA={h['FECHA']} | OBJETIVO={h['OBJETIVO']} | KANJIS={h['KANJIS']} | DURACION_MIN={h['DURACION_MIN']}")

    if not salidas:
        salidas.append("ℹ️ No detecté ni gasto ni estudio en tu mensaje.")

    return "\n".join(salidas)

if __name__ == "__main__":
    print(sophie("Mañana quiero comerme un combo cuarto de libra ($4.500) y después repasar kanjis."))
