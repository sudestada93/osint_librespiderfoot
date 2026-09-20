"""
Módulo de geolocalización IP: usa la API gratuita de ip-api.com.

ip-api.com da una ubicación aproximada de una IP (país, ciudad, proveedor
de internet, organización, coordenadas) sin necesidad de API key para uso
no comercial (límite: 45 consultas por minuto en el plan gratuito).

Si `target` es un dominio en vez de una IP, primero lo resolvemos a IP
usando el módulo DNS (nos quedamos con la primera dirección A).
"""
import re

import httpx

from . import dns_module

IP_API_URL = "http://ip-api.com/json/{query}"
# Pedimos explícitamente los campos que nos interesan (por defecto la API
# devuelve un subconjunto más chico).
FIELDS = "status,message,country,countryCode,regionName,city,zip,lat,lon,timezone,isp,org,as,query"
TIMEOUT_SECONDS = 10

IPV4_REGEX = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


def _resolve_to_ip(target: str) -> str | None:
    """Si `target` ya es una IPv4, la devuelve tal cual; si es un dominio, resuelve su primer registro A."""
    if IPV4_REGEX.match(target):
        return target
    dns_data = dns_module.run(target)
    a_records = dns_data.get("A", [])
    return a_records[0] if a_records else None


def run(target: str) -> dict:
    """Geolocaliza `target` (IP o dominio) usando ip-api.com."""
    ip = _resolve_to_ip(target)
    if not ip:
        return {"error": f"No se pudo resolver '{target}' a una dirección IP"}

    url = IP_API_URL.format(query=ip)
    try:
        response = httpx.get(url, params={"fields": FIELDS}, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        return {"error": f"No se pudo consultar ip-api.com: {exc}"}

    if data.get("status") != "success":
        return {"error": data.get("message", "ip-api.com devolvió un error desconocido")}

    return {
        "ip": data.get("query"),
        "country": data.get("country"),
        "country_code": data.get("countryCode"),
        "region": data.get("regionName"),
        "city": data.get("city"),
        "zip": data.get("zip"),
        "latitude": data.get("lat"),
        "longitude": data.get("lon"),
        "timezone": data.get("timezone"),
        "isp": data.get("isp"),
        "organization": data.get("org"),
        "as": data.get("as"),
    }
