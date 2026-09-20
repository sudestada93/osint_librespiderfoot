"""
Modelo de datos para el chequeo de contraseñas filtradas.

Va en un modelo aparte (no en scan.py) porque conceptualmente no es un
"scan": no tiene target ni se guarda en el historial.
"""
from pydantic import BaseModel, Field


class PasswordCheckRequest(BaseModel):
    password: str = Field(..., min_length=1, description="Contraseña a verificar. Nunca se guarda ni se loguea.")
