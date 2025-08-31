import os
from openai import OpenAI

api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    raise RuntimeError("❌ Falta OPENROUTER_API_KEY. Ejecuta: setx OPENROUTER_API_KEY \"sk-or-v1-...\" y abre una nueva terminal.")

client = OpenAI(
    api_key=api_key,
    base_url="https://openrouter.ai/api/v1",
)

resp = client.chat.completions.create(
    model="openai/gpt-4o-mini",  # puedes cambiar el modelo
    messages=[{"role": "user", "content": "Di 'pong' si me escuchas."}],
)

print("✅ Conexión correcta. Respuesta del modelo:")
print(resp.choices[0].message.content)
