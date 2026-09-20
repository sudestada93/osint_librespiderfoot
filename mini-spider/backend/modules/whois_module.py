"""
Módulo WHOIS: consulta la información pública de registro de un dominio.

WHOIS es un protocolo antiguo (usa el puerto TCP 43, distinto del DNS)
que permite preguntarle a un servidor "¿quién registró este dominio,
cuándo y hasta cuándo?". Cada registrador devuelve el texto con un
formato ligeramente distinto; la librería `python-whois` se encarga de
parsear las variantes más comunes a un diccionario.

Nota: algunas redes corporativas o firewalls bloquean el puerto 43.
Si este módulo siempre da timeout, probá desde otra red.
"""
from datetime import datetime

import whois as whois_lib

# Timeout en segundos para la conexión WHOIS. Si el servidor no responde
# en este tiempo, preferimos devolver un error controlado antes que
# dejar la petición HTTP colgada indefinidamente.
TIMEOUT_SECONDS = 8

# Campos que nos interesa devolver (la librería trae muchos más, pero
# estos son los útiles para un perfil OSINT básico).
FIELDS = [
    "domain_name", "registrar", "whois_server", "creation_date",
    "expiration_date", "updated_date", "name_servers", "status",
    "emails", "org", "country",
]


def _to_serializable(value):
    """Convierte fechas (datetime) —y listas de fechas— a texto plano para JSON."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_to_serializable(item) for item in value]
    return value


def run(target: str) -> dict:
    """
    Consulta el WHOIS de `target` y devuelve los campos relevantes.
    Si falla la conexión o no hay datos públicos, devuelve {"error": ...}
    en vez de propagar la excepción (así el endpoint no rompe con 500).
    """
    try:
        data = whois_lib.whois(target, timeout=TIMEOUT_SECONDS)
    except Exception as exc:
        return {"error": f"No se pudo consultar WHOIS para '{target}': {exc}"}

    # Si la librería no encontró ni el nombre de dominio, no hay datos útiles.
    if not data or not data.get("domain_name"):
        return {"error": f"Sin datos WHOIS públicos para '{target}'"}

    return {field: _to_serializable(data.get(field)) for field in FIELDS}
