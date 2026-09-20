"""
Módulo de cuentas registradas por teléfono: revisa si un número está
dado de alta en algunas plataformas, con la misma técnica que
email_accounts_module.py pero para teléfonos.

IMPORTANTE -- por qué esta lista es mucho más corta que la de email:
WhatsApp, Telegram y Signal (las plataformas más obvias para buscar por
teléfono) NO exponen esto por HTTP simple: usan protocolos propios
(MTProto, Signal Protocol, etc.) que requieren una sesión de cliente
autenticada, no una simple consulta HTTP. No es que faltó cubrirlas:
técnicamente no hay una versión gratuita y simple de esto para esas
plataformas. Lo que sí se puede cubrir son plataformas que aceptan
teléfono como identificador alternativo de una cuenta de email/usuario.

Cobertura intencionalmente priorizada sobre precisión (igual que
email_accounts_module.py): esperá más "no verificado" acá que en el
módulo de email.
"""
import asyncio

import httpx

TIMEOUT_SECONDS = 10
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


async def _check_microsoft(client: httpx.AsyncClient, phone: str) -> dict:
    """
    Las cuentas de Microsoft se pueden identificar por teléfono además
    de por email -- este es el mismo endpoint que usa email_accounts_module,
    con el mismo problema de confiabilidad confirmado: solo reporta
    cuando SÍ encuentra la cuenta, nunca afirma que no existe.
    """
    try:
        response = await client.post(
            "https://login.microsoftonline.com/common/GetCredentialType",
            json={"Username": phone},
            timeout=TIMEOUT_SECONDS,
        )
        data = response.json()
        if data.get("IfExistsResult") == 0:
            return {"platform": "Microsoft", "exists": True}
        return {
            "platform": "Microsoft",
            "exists": None,
            "error": "resultado no confiable para 'no existe' (mismo caso que en email_accounts)",
        }
    except Exception as exc:
        return {"platform": "Microsoft", "exists": None, "error": str(exc)}


async def _check_instagram(client: httpx.AsyncClient, phone: str) -> dict:
    """
    Instagram permite registrarse con teléfono, así que su validación de
    registro debería aceptar teléfonos igual que acepta emails. Menor
    confianza que la versión para email: no se pudo confirmar en vivo
    que este endpoint también valide teléfonos de la misma forma.
    """
    try:
        response = await client.post(
            "https://www.instagram.com/api/v1/web/accounts/check_email/",
            data={"email": phone},
            headers={"X-CSRFToken": "missing"},
            timeout=TIMEOUT_SECONDS,
        )
        data = response.json()
        if "user_exists" not in data:
            return {"platform": "Instagram", "exists": None, "error": "respuesta inesperada"}
        return {"platform": "Instagram", "exists": bool(data["user_exists"])}
    except Exception as exc:
        return {"platform": "Instagram", "exists": None, "error": str(exc)}


CHECKERS = [
    _check_microsoft,
    _check_instagram,
]


async def run(phone: str) -> dict:
    """Revisa en paralelo si `phone` está registrado en las plataformas de CHECKERS."""
    phone = phone.strip()
    if not phone:
        return {"error": "El teléfono no puede estar vacío"}

    async with httpx.AsyncClient(headers=HEADERS) as client:
        results = await asyncio.gather(*(checker(client, phone) for checker in CHECKERS))

    registered_on = [r["platform"] for r in results if r.get("exists") is True]
    not_registered_on = [r["platform"] for r in results if r.get("exists") is False]
    unchecked = [r for r in results if r.get("exists") is None]

    return {
        "registered_on": registered_on,
        "not_registered_on": not_registered_on,
        "unchecked": unchecked,
        "total_checked": len(results),
        "note": (
            "Cobertura limitada a propósito: WhatsApp/Telegram/Signal no exponen "
            "esto por HTTP simple (usan protocolos propios)."
        ),
    }
