FROM python:3.11-slim

WORKDIR /app

# Dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código
COPY . .

ENV PORT=8080
EXPOSE 8080

# Ejecuta Flask (archivo sophie_api.py → objeto app)
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "sophie_api:app"]
