"""
Módulo de contraseñas filtradas: revisa si una contraseña puntual
apareció en bases de datos de brechas conocidas, usando la API pública
"Pwned Passwords" de Have I Been Pwned (gratis, sin API key).

Es seguro por diseño (k-anonymity): la contraseña NUNCA sale completa
de acá. Se calcula su hash SHA-1 localmente, se mandan solo los
primeros 5 caracteres de ese hash a la API, y esta devuelve TODOS los
hashes que empiezan igual (normalmente varios cientos o miles) -- la
comparación final para ver si tu hash completo está en esa lista se
hace acá mismo, en tu máquina. La API nunca recibe la contraseña ni el
hash completo, así que no hay forma de que "adivine" cuál era.

IMPORTANTE: a diferencia de todos los demás módulos, este resultado
NUNCA se guarda en el historial ni en la base de datos -- ni la
contraseña, ni su hash, ni el resultado. Se calcula al momento y ahí
se termina. No hay un endpoint "GET" para este módulo (para que la
contraseña nunca quede en la URL ni en logs del navegador/servidor).
"""
import hashlib

import httpx

API_URL = "https://api.pwnedpasswords.com/range/{prefix}"
TIMEOUT_SECONDS = 10


def check_password(password: str) -> dict:
    """Consulta si `password` apareció en brechas conocidas. Nunca guarda ni loguea la contraseña."""
    if not password:
        return {"error": "La contraseña no puede estar vacía"}

    sha1_hash = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    prefix, suffix = sha1_hash[:5], sha1_hash[5:]

    try:
        response = httpx.get(
            API_URL.format(prefix=prefix),
            timeout=TIMEOUT_SECONDS,
            headers={"Add-Padding": "true"},  # oculta el tamaño real de la respuesta
        )
        response.raise_for_status()
    except Exception as exc:
        return {"error": f"No se pudo consultar el servicio de contraseñas filtradas: {exc}"}

    times_seen = 0
    for line in response.text.splitlines():
        line_suffix, _, count = line.partition(":")
        if line_suffix.strip() == suffix:
            times_seen = int(count)
            break

    return {
        "was_breached": times_seen > 0,
        "times_seen": times_seen,
    }
