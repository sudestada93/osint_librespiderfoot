"""
Módulo de cuentas registradas por email: revisa si un email está dado
de alta en varias plataformas grandes, usando el mismo mecanismo
público que usa el formulario de esas plataformas para avisarte "ese
email ya tiene cuenta" al registrarte o al pedir recuperar la
contraseña. No inicia sesión en ningún lado, ni intenta entrar a
ninguna cuenta: solo lee la respuesta pública que cada sitio ya da por
su cuenta al validar un email.

Es la misma técnica que usan herramientas como Holehe. Dos advertencias
importantes:

  1. Ningún sitio documenta oficialmente este comportamiento -- lo
     pueden cambiar en cualquier momento sin avisar. Un "no encontrado"
     NO es garantía absoluta de que la cuenta no exista.
  2. Consultar muchos emails seguido puede hacer que el sitio te
     bloquee temporalmente la IP. Usalo con moderación, no en un loop.

No se pudo verificar en vivo el comportamiento exacto de cada
plataforma durante el desarrollo (red restringida del entorno de
pruebas): revisá los resultados con sentido crítico la primera vez que
lo uses.
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


async def _check_microsoft(client: httpx.AsyncClient, email: str) -> dict:
    """
    login.microsoftonline.com expone públicamente el endpoint que usa su
    propio formulario de login. IfExistsResult == 0 está documentado
    como "la cuenta existe" -- pero en las pruebas de este proyecto dio
    un falso negativo confirmado (marcó "no existe" para una cuenta real
    y conocida). Por eso acá solo confiamos en el resultado cuando dice
    que SÍ existe; cualquier otro caso queda como "no verificado" en vez
    de afirmar que la cuenta no existe.
    """
    try:
        response = await client.post(
            "https://login.microsoftonline.com/common/GetCredentialType",
            json={"Username": email},
            timeout=TIMEOUT_SECONDS,
        )
        data = response.json()
        if data.get("IfExistsResult") == 0:
            return {"platform": "Microsoft", "exists": True}
        return {
            "platform": "Microsoft",
            "exists": None,
            "error": "resultado no confiable para 'no existe' (ver docstring); no se puede confirmar la ausencia",
        }
    except Exception as exc:
        return {"platform": "Microsoft", "exists": None, "error": str(exc)}


async def _check_mozilla(client: httpx.AsyncClient, email: str) -> dict:
    """La API pública de cuentas de Mozilla (Firefox Sync) tiene un endpoint de status dedicado."""
    try:
        response = await client.get(
            "https://api.accounts.firefox.com/v1/account/status",
            params={"email": email},
            timeout=TIMEOUT_SECONDS,
        )
        data = response.json()
        return {"platform": "Mozilla (Firefox)", "exists": bool(data.get("exists"))}
    except Exception as exc:
        return {"platform": "Mozilla (Firefox)", "exists": None, "error": str(exc)}


async def _check_duolingo(client: httpx.AsyncClient, email: str) -> dict:
    """La API pública de Duolingo devuelve una lista de usuarios que coinciden con el email."""
    try:
        response = await client.get(
            "https://www.duolingo.com/2017-06-30/users",
            params={"email": email},
            timeout=TIMEOUT_SECONDS,
        )
        data = response.json()
        users = data.get("users") or []
        return {"platform": "Duolingo", "exists": len(users) > 0}
    except Exception as exc:
        return {"platform": "Duolingo", "exists": None, "error": str(exc)}


async def _check_instagram(client: httpx.AsyncClient, email: str) -> dict:
    """El formulario de recuperación de cuenta de Instagram valida el email antes de enviar nada."""
    try:
        response = await client.post(
            "https://www.instagram.com/api/v1/web/accounts/check_email/",
            data={"email": email},
            headers={"X-CSRFToken": "missing"},
            timeout=TIMEOUT_SECONDS,
        )
        data = response.json()
        return {"platform": "Instagram", "exists": bool(data.get("user_exists"))}
    except Exception as exc:
        return {"platform": "Instagram", "exists": None, "error": str(exc)}


async def _check_spotify(client: httpx.AsyncClient, email: str) -> dict:
    """El formulario de registro de Spotify valida el email en tiempo real mientras escribís."""
    try:
        response = await client.get(
            "https://spclient.wg.spotify.com/signup/public/v1/account",
            params={"validate": 1, "email": email},
            timeout=TIMEOUT_SECONDS,
        )
        data = response.json()
        # status 20 = "ya existe una cuenta con ese email" (documentado por la comunidad OSINT)
        return {"platform": "Spotify", "exists": data.get("status") == 20}
    except Exception as exc:
        return {"platform": "Spotify", "exists": None, "error": str(exc)}


async def _check_adobe(client: httpx.AsyncClient, email: str) -> dict:
    """El login de Adobe responde distinto según si el email tiene cuenta creada."""
    try:
        response = await client.get(
            "https://auth.services.adobe.com/signin/v2/users/accounts",
            params={"realm": "Username", "email": email, "requestId": "minispider"},
            timeout=TIMEOUT_SECONDS,
        )
        # Adobe no siempre da un campo JSON simple y estable: nos apoyamos
        # en el status code (200 = encontrado) y, si no, lo dejamos como
        # "no verificado" en vez de asumir que no existe.
        if response.status_code == 200:
            return {"platform": "Adobe", "exists": True}
        if response.status_code == 404:
            return {"platform": "Adobe", "exists": False}
        return {"platform": "Adobe", "exists": None, "error": f"status HTTP inesperado: {response.status_code}"}
    except Exception as exc:
        return {"platform": "Adobe", "exists": None, "error": str(exc)}


CHECKERS = [
    _check_microsoft,
    _check_mozilla,
    _check_duolingo,
    _check_instagram,
    _check_spotify,
    _check_adobe,
]


async def run(email: str) -> dict:
    """Revisa en paralelo si `email` está registrado en las plataformas de CHECKERS."""
    email = email.strip().lower()
    if "@" not in email:
        return {"error": f"'{email}' no parece un email válido"}

    async with httpx.AsyncClient(headers=HEADERS) as client:
        results = await asyncio.gather(*(checker(client, email) for checker in CHECKERS))

    registered_on = [r["platform"] for r in results if r.get("exists") is True]
    not_registered_on = [r["platform"] for r in results if r.get("exists") is False]
    unchecked = [r for r in results if r.get("exists") is None]

    return {
        "registered_on": registered_on,
        "not_registered_on": not_registered_on,
        "unchecked": unchecked,
        "total_checked": len(results),
    }
