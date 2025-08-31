import os
from openai import OpenAI

# 1. Tomamos la clave desde la variable de entorno
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError("❌ No encontré la variable OPENAI_API_KEY. Revisa el paso 4.")

# 2. Iniciamos el cliente con esa clave
client = OpenAI(api_key=api_key)

# 3. Hacemos una llamada mínima de prueba
resp = client.chat.completions.create(
    model="gpt-5-mini",  # modelo barato y rápido, ideal para test
    messages=[{"role": "user", "content": "Escribe la palabra 'pong' si me escuchas."}]
)

print("✅ Conexión correcta. Respuesta del modelo:")
print(resp.choices[0].message.content)
