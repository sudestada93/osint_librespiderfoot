"""
Modelo de datos para pedir un scan completo (POST /api/scan).

Pydantic valida automáticamente el JSON que manda el frontend: si falta
`target` o algún tipo no coincide, FastAPI devuelve un 422 con el detalle
del error, sin que tengamos que escribir esa validación a mano.
"""
from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    target: str = Field(..., min_length=1, description="Dominio, IP o host a analizar")
    modules: list[str] | None = Field(
        None,
        description="Módulos a ejecutar (ver GET /api/modules). Si se omite, corre todos menos 'ports'.",
    )
    ports: str | None = Field(None, description="Spec de puertos para el módulo 'ports' (ej: 'all', '1-1024')")
    ports_timeout: float = Field(1.5, gt=0, description="Timeout por puerto, en segundos")
    ports_concurrency: int = Field(500, gt=0, le=5000, description="Conexiones simultáneas máximas")
    ssl_port: int = Field(443, gt=0, le=65535, description="Puerto a usar para el módulo SSL/TLS")
