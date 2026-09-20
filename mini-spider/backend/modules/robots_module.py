"""
Módulo robots.txt / sitemap.xml: descarga esos dos archivos (si existen)
y extrae las rutas que mencionan.

robots.txt le pide a los buscadores que NO indexen ciertas rutas, pero
sigue siendo un archivo público que cualquiera puede leer -- y a veces
"delata" rutas que el dueño del sitio prefería mantener discretas
(paneles de admin, backups, entornos de staging).
sitemap.xml, al revés, lista las páginas que el sitio SÍ quiere que se
indexen.
"""
from xml.etree import ElementTree

import httpx

TIMEOUT_SECONDS = 10
MAX_SITEMAP_URLS = 200  # tope para no devolver una respuesta gigante


def _fetch(url: str) -> str | None:
    """Descarga `url` como texto. Devuelve None ante cualquier fallo o status != 200."""
    try:
        response = httpx.get(url, timeout=TIMEOUT_SECONDS, follow_redirects=True)
    except Exception:
        return None
    return response.text if response.status_code == 200 else None


def _parse_robots(text: str) -> dict:
    """Extrae las directivas Disallow/Allow/Sitemap de un robots.txt."""
    disallow, allow, sitemaps = [], [], []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key, value = key.strip().lower(), value.strip()
        if key == "disallow" and value:
            disallow.append(value)
        elif key == "allow" and value:
            allow.append(value)
        elif key == "sitemap" and value:
            sitemaps.append(value)
    return {"disallow": disallow, "allow": allow, "sitemaps": sitemaps}


def _parse_sitemap(text: str) -> list[str]:
    """Extrae las URLs (<loc>) de un sitemap.xml."""
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError:
        return []
    # Los tags vienen con namespace (ej. "{http://...}loc"), por eso
    # comparamos con endswith en vez de igualdad exacta.
    return [elem.text.strip() for elem in root.iter() if elem.tag.endswith("loc") and elem.text]


def run(target: str) -> dict:
    """Busca y parsea robots.txt y sitemap.xml de `target`."""
    robots_data = None
    sitemap_candidates = []

    for scheme in ("https", "http"):
        robots_text = _fetch(f"{scheme}://{target}/robots.txt")
        if robots_text is not None:
            robots_data = _parse_robots(robots_text)
            sitemap_candidates = robots_data["sitemaps"] or [f"{scheme}://{target}/sitemap.xml"]
            break

    if not sitemap_candidates:
        sitemap_candidates = [f"https://{target}/sitemap.xml", f"http://{target}/sitemap.xml"]

    sitemap_urls = []
    for sitemap_url in sitemap_candidates:
        sitemap_text = _fetch(sitemap_url)
        if sitemap_text is not None:
            sitemap_urls = _parse_sitemap(sitemap_text)[:MAX_SITEMAP_URLS]
            break

    if robots_data is None and not sitemap_urls:
        return {"error": f"No se encontró robots.txt ni sitemap.xml en '{target}'"}

    return {"robots_txt": robots_data, "sitemap_urls": sitemap_urls}
