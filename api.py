from fastapi import FastAPI
from pydantic import BaseModel
from sophie import sophie  # tu función sophie(mensaje)

app = FastAPI()

class Input(BaseModel):
    mensaje: str

@app.get("/")
def root():
    return {"ok": True, "msg": "Sophie API viva"}

@app.post("/procesar")
def procesar(input: Input):
    salida = sophie(input.mensaje)
    return {"respuesta": salida}
