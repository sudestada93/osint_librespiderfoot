"""
Módulo de headers HTTP: consulta las cabeceras que devuelve un servidor
web y detecta pistas básicas sobre las tecnologías que usa.

Las cabeceras HTTP ("headers") son metadata que el servidor manda junto
con la página: a veces revelan el software del servidor (nginx, Apache),
el lenguaje/framework (X-Powered-By: PHP) o un CMS (X-Generator:
WordPress). No es un fingerprinting exhaustivo tipo Wappalyzer, son
señales simples y gratuitas.
"""
import httpx

TIMEOUT_SECONDS = 10

# Si aparece esta cookie en el header Set-Cookie, es una pista fuerte de
# qué tecnología corre detrás (cada framework tiene su propio nombre de
# cookie de sesión por defecto).
COOKIE_HINTS = {
    "phpsessid": "PHP",
    "jsessionid": "Java (JSP/Servlet)",
    "asp.net_sessionid": "ASP.NET",
    "laravel_session": "Laravel (PHP)",
    "wordpress_logged_in": "WordPress",
    "csrftoken": "Django (Python)",
}


def run(target: str) -> dict:
    """Descarga la página principal de `target` y analiza sus headers HTTP."""
    for scheme in ("https", "http"):
        url = f"{scheme}://{target}"
        try:
            response = httpx.get(url, timeout=TIMEOUT_SECONDS, follow_redirects=True)
        except Exception:
            continue  # probamos el otro esquema

        headers = {k.lower(): v for k, v in response.headers.items()}
        technologies = set()

        for header_name in ("server", "x-powered-by", "x-generator"):
            if header_name in headers:
                technologies.add(headers[header_name])

        cookie_header = headers.get("set-cookie", "").lower()
        for cookie_name, tech in COOKIE_HINTS.items():
            if cookie_name in cookie_header:
                technologies.add(tech)

        return {
            "final_url": str(response.url),
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "technologies": sorted(technologies),
        }

    return {"error": f"No se pudo conectar a '{target}' ni por HTTPS ni por HTTP"}
