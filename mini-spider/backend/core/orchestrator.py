"""
Orquestador de módulos: corre varios módulos de reconocimiento en
paralelo contra el mismo objetivo y junta sus resultados en un solo
diccionario.

La mayoría de los módulos son funciones síncronas normales (hacen una
llamada de red y esperan la respuesta bloqueando ese hilo). El módulo de
puertos ya es asíncrono (abre miles de conexiones a la vez con asyncio).
Para correr todo en paralelo sin tener que reescribir los módulos
síncronos, usamos `asyncio.to_thread` para esos y los mezclamos con los
asíncronos en un mismo `asyncio.gather`.
"""
import asyncio
from typing import Callable

from ..modules import (
    dns_module,
    email_lookup_module,
    emails_module,
    geoip_module,
    headers_module,
    phone_lookup_module,
    ports_module,
    robots_module,
    ssl_module,
    subdomains_module,
    username_lookup_module,
    wayback_module,
    whois_module,
)

# Registro central: nombre de módulo -> función run(target, **kwargs).
# Separamos los síncronos de los asíncronos porque se invocan distinto.
SYNC_MODULES: dict[str, Callable] = {
    "dns": dns_module.run,
    "whois": whois_module.run,
    "subdomains": subdomains_module.run,
    "ssl": ssl_module.run,
    "emails": emails_module.run,
    "geoip": geoip_module.run,
    "headers": headers_module.run,
    "robots": robots_module.run,
    "wayback": wayback_module.run,
    "email_lookup": email_lookup_module.run,
    "phone_lookup": phone_lookup_module.run,
}

ASYNC_MODULES: dict[str, Callable] = {
    "ports": ports_module.run,
    "username_lookup": username_lookup_module.run,
}

ALL_MODULE_NAMES = sorted(set(SYNC_MODULES) | set(ASYNC_MODULES))

# El escaneo de puertos es el único módulo ACTIVO (genera tráfico real
# contra el objetivo) y puede ser lento si se pide un rango grande, así
# que no se incluye en un scan "por defecto": hay que pedirlo explícito.
DEFAULT_MODULES = [name for name in ALL_MODULE_NAMES if name != "ports"]

# Qué tipos de objetivo (ver core/target_utils.py) tiene sentido pasarle
# a cada módulo. No tiene sentido correr WHOIS sobre un email, o el
# lookup de teléfono sobre un dominio.
MODULE_TARGET_TYPES: dict[str, set[str]] = {
    "dns": {"domain"},
    "whois": {"domain"},
    "subdomains": {"domain"},
    "ssl": {"domain", "ip"},
    "emails": {"domain"},
    "geoip": {"domain", "ip"},
    "headers": {"domain", "ip"},
    "robots": {"domain"},
    "wayback": {"domain"},
    "ports": {"domain", "ip"},
    "email_lookup": {"email"},
    "phone_lookup": {"phone"},
    "username_lookup": {"username"},
}


def modules_for_target_type(target_type: str) -> list[str]:
    """Devuelve todos los módulos aplicables a `target_type` (incluye 'ports' si corresponde)."""
    return sorted(name for name, types in MODULE_TARGET_TYPES.items() if target_type in types)


def default_modules_for_target_type(target_type: str) -> list[str]:
    """Igual que modules_for_target_type, pero sin 'ports' (el único módulo activo)."""
    return [name for name in modules_for_target_type(target_type) if name != "ports"]


async def run_scan(
    target: str,
    modules: list[str] | None = None,
    module_kwargs: dict[str, dict] | None = None,
) -> dict:
    """
    Corre los módulos indicados (o DEFAULT_MODULES si no se especifica)
    contra `target`, todos en paralelo, y devuelve
    {nombre_de_modulo: resultado_del_modulo}.

    Si un módulo tira una excepción inesperada (no controlada dentro del
    propio módulo), no tumba el scan entero: esa entrada queda con un
    {"error": "..."} y los demás módulos siguen su curso normal.
    """
    selected = modules if modules is not None else DEFAULT_MODULES
    module_kwargs = module_kwargs or {}

    unknown = [name for name in selected if name not in ALL_MODULE_NAMES]
    if unknown:
        raise ValueError(f"Módulo(s) desconocido(s): {', '.join(unknown)}")

    coroutines = {}
    for name in selected:
        kwargs = module_kwargs.get(name, {})
        if name in ASYNC_MODULES:
            coroutines[name] = ASYNC_MODULES[name](target, **kwargs)
        else:
            coroutines[name] = asyncio.to_thread(SYNC_MODULES[name], target, **kwargs)

    results = await asyncio.gather(*coroutines.values(), return_exceptions=True)

    output = {}
    for name, result in zip(coroutines.keys(), results):
        if isinstance(result, Exception):
            output[name] = {"error": f"Fallo inesperado en el módulo '{name}': {result}"}
        else:
            output[name] = result
    return output
