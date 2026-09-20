"""
Módulo de cuentas registradas por email: revisa si un email está dado
de alta en más de cien sitios, usando la librería `holehe`
(https://github.com/megadose/holehe -- open-source, MIT license,
mantenida por la comunidad OSINT, gratis, sin API key) como motor
principal, más dos checkers propios para sitios que holehe no cubre
(Microsoft cuenta personal, Duolingo).

`holehe` prueba el mismo mecanismo público que usa el formulario de
"¿ya tenés cuenta?" o "olvidé mi contraseña" de cada sitio -- no inicia
sesión en ningún lado. Se usa acá como librería (no su CLI): se
importan sus módulos y se corren todos en paralelo con asyncio +
httpx (holehe ya usa httpx internamente, compatible con el resto de
MiniSpider sin adaptar nada).

Priorizamos cobertura por sobre precisión perfecta (decisión explícita
del proyecto). Advertencias:

  1. Ningún sitio documenta oficialmente este comportamiento -- lo
     pueden cambiar sin avisar. Un "no encontrado" NO es garantía.
  2. Consultar muchos emails seguido puede hacer que algunos sitios
     bloqueen temporalmente tu IP. Usalo con moderación, no en un loop.
  3. Cuando holehe detecta que un sitio lo bloqueó/limitó (rate limit),
     lo tratamos como "no verificado", nunca como "no existe" -- para
     no repetir el falso negativo que tuvimos con Microsoft.
  4. El checker de Microsoft (cuenta personal, no cubierto por holehe)
     tuvo un falso negativo CONFIRMADO en pruebas reales: por eso solo
     reporta cuando SÍ encuentra la cuenta, nunca cuando no la encuentra.
"""
import asyncio

import httpx
from holehe.core import get_functions, import_submodules, launch_module

TIMEOUT_SECONDS = 10
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

# Cargamos los módulos de holehe una sola vez al importar este archivo
# (no en cada consulta), para no pagar ese costo de importación en cada scan.
_HOLEHE_MODULES = import_submodules("holehe.modules")
_HOLEHE_WEBSITES = get_functions(_HOLEHE_MODULES)


async def _check_microsoft(client: httpx.AsyncClient, email: str) -> dict:
    """
    login.microsoftonline.com expone públicamente el endpoint que usa su
    propio formulario de login para cuentas PERSONALES de Microsoft (no
    cubierto por holehe, que solo chequea Office 365 corporativo).
    IfExistsResult == 0 está documentado como "la cuenta existe" -- pero
    tuvo un falso negativo confirmado en pruebas reales (marcó "no
    existe" una cuenta real y conocida). Por eso acá solo confiamos en
    el resultado cuando dice que SÍ existe.
    """
    try:
        response = await client.post(
            "https://login.microsoftonline.com/common/GetCredentialType",
            json={"Username": email},
            timeout=TIMEOUT_SECONDS,
        )
        data = response.json()
        if data.get("IfExistsResult") == 0:
            return {"domain": "microsoft.com (cuenta personal)", "exists": True}
        return {
            "domain": "microsoft.com (cuenta personal)",
            "exists": None,
            "error": "resultado no confiable para 'no existe' (falso negativo confirmado)",
        }
    except Exception as exc:
        return {"domain": "microsoft.com (cuenta personal)", "exists": None, "error": str(exc)}


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
        return {"domain": "duolingo.com", "exists": len(users) > 0}
    except Exception as exc:
        return {"domain": "duolingo.com", "exists": None, "error": str(exc)}


async def run(email: str) -> dict:
    """Revisa en paralelo si `email` está registrado en los sitios que cubre holehe + los checkers propios."""
    email = email.strip().lower()
    if "@" not in email:
        return {"error": f"'{email}' no parece un email válido"}

    holehe_out: list[dict] = []
    async with httpx.AsyncClient(headers=HEADERS, timeout=TIMEOUT_SECONDS) as client:
        holehe_task = asyncio.gather(
            *(launch_module(website, email, client, holehe_out) for website in _HOLEHE_WEBSITES),
            return_exceptions=True,
        )
        extra_task = asyncio.gather(
            _check_microsoft(client, email),
            _check_duolingo(client, email),
        )
        await asyncio.gather(holehe_task, extra_task)
        extra_results = extra_task.result()

    registered_on = sorted(r["domain"] for r in holehe_out if r.get("exists") is True)
    not_registered_on = sorted(
        r["domain"] for r in holehe_out if r.get("exists") is False and not r.get("rateLimit")
    )
    unchecked = [
        {"platform": r["domain"], "exists": None, "error": "rate limit / bloqueo del sitio"}
        for r in holehe_out
        if r.get("rateLimit")
    ]

    for r in extra_results:
        if r.get("exists") is True:
            registered_on.append(r["domain"])
        elif r.get("exists") is False:
            not_registered_on.append(r["domain"])
        else:
            unchecked.append({"platform": r["domain"], "exists": None, "error": r.get("error")})

    return {
        "registered_on": sorted(registered_on),
        "not_registered_on": sorted(not_registered_on),
        "unchecked": unchecked,
        "total_checked": len(holehe_out) + len(extra_results),
    }
