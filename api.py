# api.py
import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.get("/health")
def health():
    # Northflank comprobará esta ruta; debe responder 200
    return jsonify(ok=True), 200

@app.get("/")
def home():
    return "Sophie API viva ✅", 200

if __name__ == "__main__":
    # CLAVE: usar el puerto que Northflank inyecta en la env PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
