FROM python:3.11-slim

WORKDIR /app

# Copiamos primero requirements para instalar deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos todo el código
COPY . .

ENV PORT=8080
EXPOSE 8080

# Ejecuta Flask con Gunicorn (api.py → app)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "sophie_api:app"]
