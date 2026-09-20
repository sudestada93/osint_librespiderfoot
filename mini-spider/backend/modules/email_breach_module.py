"""
Módulo de brechas de datos por email: revisa si un email aparece en
bases de datos de brechas conocidas, usando la API pública y gratuita
de XposedOrNot (https://xposedornot.com) -- sin API key.

A diferencia de Have I Been Pwned (que dejó de tener plan gratuito para
buscar por email de forma automatizada), XposedOrNot sigue ofreciendo
esta consulta gratis por API. No tiene la misma base de datos ni
trayectoria que HIBP, así que conviene tratarlo como una señal
adicional, no como la verdad absoluta.

Si querés además la opinión de HIBP: su sitio web (haveibeenpwned.com)
se puede seguir usando gratis A MANO, un email por vez, en el
navegador -- lo que dejó de ser gratis es su API para automatizar
consultas como esta.
"""
import httpx

API_URL = "https://api.xposedornot.com/v1/check-email/{email}"
TIMEOUT_SECONDS = 10


def run(email: str) -> dict:
    """Consulta si `email` aparece en brechas de datos conocidas."""
    email = email.strip().lower()
    if "@" not in email:
        return {"error": f"'{email}' no parece un email válido"}

    try:
        response = httpx.get(API_URL.format(email=email), timeout=TIMEOUT_SECONDS)
    except Exception as exc:
        return {"error": f"No se pudo consultar XposedOrNot: {exc}"}

    # XposedOrNot devuelve 404 cuando el email no aparece en ninguna brecha conocida.
    if response.status_code == 404:
        return {"was_breached": False, "breaches": [], "total_breaches": 0}

    if response.status_code != 200:
        return {"error": f"XposedOrNot devolvió un status inesperado: {response.status_code}"}

    try:
        data = response.json()
    except ValueError:
        return {"error": "XposedOrNot devolvió una respuesta que no se pudo interpretar como JSON"}

    breaches_field = data.get("breaches")
    if not breaches_field:
        return {"was_breached": False, "breaches": [], "total_breaches": 0}

    # La API anida la lista de nombres de brechas dentro de otra lista: [["Adobe", "LinkedIn", ...]]
    breach_names = breaches_field[0] if isinstance(breaches_field[0], list) else breaches_field
    return {"was_breached": True, "breaches": breach_names, "total_breaches": len(breach_names)}
