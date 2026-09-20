"""
Módulo de búsqueda de username: revisa en paralelo si un nombre de
usuario existe en una lista de plataformas conocidas, visitando la URL
de perfil público de cada una (el mismo principio que usan herramientas
como Sherlock).

Es "best-effort" a propósito: cada sitio puede cambiar su estructura o
empezar a bloquear peticiones automatizadas en cualquier momento, y
varias plataformas grandes (Instagram, TikTok, Twitter/X, Pinterest)
tienen protecciones anti-bot que pueden devolver falsos positivos o
falsos negativos. Un "no encontrado" acá NO es garantía de que el
username no exista en esa plataforma -- es una señal, no una certeza.
"""
import asyncio

import httpx

TIMEOUT_SECONDS = 8

# Un User-Agent de navegador real evita que algunos sitios rechacen la
# petición de entrada solo por parecer un bot/script.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

# (nombre del sitio, url con {username}, código HTTP que indica "existe").
# Plataformas confiables (comportamiento simple: 200 = existe, 404 = no)
# mezcladas con otras más grandes que tienen anti-bot y pueden dar ruido
# (se incluyen igual porque el usuario prefirió cobertura amplia).
PLATFORMS = [
    ("GitHub", "https://github.com/{username}", 200),
    ("GitLab", "https://gitlab.com/{username}", 200),
    ("Reddit", "https://www.reddit.com/user/{username}", 200),
    ("Telegram", "https://t.me/{username}", 200),
    ("Steam", "https://steamcommunity.com/id/{username}", 200),
    ("Twitch", "https://www.twitch.tv/{username}", 200),
    ("Medium", "https://medium.com/@{username}", 200),
    ("HackerNews", "https://news.ycombinator.com/user?id={username}", 200),
    ("npm", "https://www.npmjs.com/~{username}", 200),
    ("Instagram", "https://www.instagram.com/{username}/", 200),
    ("TikTok", "https://www.tiktok.com/@{username}", 200),
    ("Twitter/X", "https://x.com/{username}", 200),
    ("Pinterest", "https://www.pinterest.com/{username}/", 200),
]


async def _check_platform(client: httpx.AsyncClient, name: str, url_template: str, username: str) -> dict:
    """Visita la URL de perfil de `username` en una plataforma y evalúa si existe."""
    url = url_template.format(username=username)
    try:
        response = await client.get(url, timeout=TIMEOUT_SECONDS, follow_redirects=True)
        return {"platform": name, "url": url, "exists": response.status_code == 200, "status_code": response.status_code}
    except Exception as exc:
        # No pudimos determinar nada (timeout, DNS, bloqueo de red): lo
        # dejamos como "no verificado" en vez de asumir que no existe.
        return {"platform": name, "url": url, "exists": None, "error": str(exc)}


async def run(username: str) -> dict:
    """Chequea la existencia de `username` en las plataformas de PLATFORMS, en paralelo."""
    username = username.strip()
    if not username:
        return {"error": "El username no puede estar vacío"}

    async with httpx.AsyncClient(headers=HEADERS) as client:
        tasks = [_check_platform(client, name, url, username) for name, url, _ in PLATFORMS]
        results = await asyncio.gather(*tasks)

    found = [r for r in results if r["exists"] is True]
    unchecked = [r for r in results if r["exists"] is None]
    not_found = [r for r in results if r["exists"] is False]

    return {
        "username": username,
        "found_on": found,
        "not_found_on": [r["platform"] for r in not_found],
        "unchecked": unchecked,
        "total_checked": len(results),
    }
