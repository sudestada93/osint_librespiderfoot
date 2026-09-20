"""
Módulo de lookup de email: información pública sobre UNA dirección de
correo puntual (a diferencia de emails_module.py, que busca emails QUE
PERTENECEN a un dominio, este analiza un email específico que ya tenés).

Fuentes, todas gratis y sin API key:
  - Validación de formato y extracción del dominio
  - Registros MX del dominio (reutiliza dns_module): si no tiene MX,
    ese dominio probablemente no puede recibir correo real
  - Gravatar: muchísimos sitios usan Gravatar para la foto de perfil;
    si el email tiene un perfil público ahí, lo mostramos con su link
  - Lista local de dominios de email descartables/temporales conocidos

Nota: no incluimos verificación de brechas de datos (breach check, tipo
Have I Been Pwned) porque ese servicio dejó de tener un plan gratuito
para búsqueda por email -- no queríamos depender de una API paga.
"""
import hashlib

import httpx

from . import dns_module

GRAVATAR_URL = "https://www.gravatar.com/{md5_hash}.json"
TIMEOUT_SECONDS = 8

# Lista corta de dominios de email temporales/descartables más conocidos.
# No pretende ser exhaustiva (hay listas públicas de miles de dominios),
# pero cubre los más comunes sin depender de un servicio externo.
DISPOSABLE_DOMAINS = {
    "mailinator.com", "10minutemail.com", "guerrillamail.com", "tempmail.com",
    "yopmail.com", "trashmail.com", "throwawaymail.com", "getnada.com",
    "temp-mail.org", "fakeinbox.com", "sharklasers.com", "dispostable.com",
}


def _check_gravatar(email: str) -> dict | None:
    """Busca un perfil público de Gravatar asociado al email. Devuelve None si no hay o falla la consulta."""
    md5_hash = hashlib.md5(email.encode()).hexdigest()
    url = GRAVATAR_URL.format(md5_hash=md5_hash)
    try:
        response = httpx.get(url, timeout=TIMEOUT_SECONDS, follow_redirects=True)
    except Exception:
        return None
    if response.status_code != 200:
        return None
    try:
        data = response.json()
    except ValueError:
        return None

    entries = data.get("entry")
    if not entries:
        return None
    entry = entries[0]
    return {
        "profile_url": entry.get("profileUrl"),
        "display_name": entry.get("displayName"),
        "avatar_url": f"https://www.gravatar.com/avatar/{md5_hash}",
    }


def run(email: str) -> dict:
    """Analiza un email puntual: dominio, MX, si es descartable, y si tiene Gravatar público."""
    email = email.strip().lower()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        return {"error": f"'{email}' no parece un email válido"}

    _local_part, _, domain = email.partition("@")

    dns_data = dns_module.run(domain)
    mx_records = dns_data.get("MX", [])
    has_mail_server = bool(mx_records)

    return {
        "email": email,
        "domain": domain,
        "has_mail_server": has_mail_server,
        "mx_records": mx_records,
        "is_disposable_domain": domain in DISPOSABLE_DOMAINS,
        "gravatar": _check_gravatar(email),
    }
