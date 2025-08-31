# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Evita archivos .pyc y buffers
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Dependencias del sistema (opcionales, psycopg2-binary ya las trae)
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

# Dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código
COPY . .

# Arranque SIEMPRE con api.py
CMD ["python", "api.py"]
