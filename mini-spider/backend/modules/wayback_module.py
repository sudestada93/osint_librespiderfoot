"""
Módulo Wayback Machine: busca URLs históricas archivadas de un dominio
usando la API CDX del Internet Archive (web.archive.org), gratuita y sin
necesidad de API key.

Sirve para encontrar rutas o subdominios que existieron en el pasado y
ya no están enlazados desde ningún lado, pero que Wayback Machine igual
capturó en algún momento (útil para encontrar paneles viejos, backups
olvidados, versiones anteriores del sitio, etc.).
"""
import httpx

CDX_URL = "https://web.archive.org/cdx/search/cdx"
TIMEOUT_SECONDS = 20
MAX_RESULTS = 500


def run(target: str) -> dict:
    """Consulta snapshots históricos de `target` (y sus rutas) en Wayback Machine."""
    params = {
        "url": f"{target}/*",
        "output": "json",
        "fl": "original,timestamp",
        "collapse": "urlkey",  # evita duplicados de la misma URL en distintas fechas
        "limit": str(MAX_RESULTS),
    }
    try:
        response = httpx.get(CDX_URL, params=params, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        rows = response.json()
    except Exception as exc:
        return {"error": f"No se pudo consultar Wayback Machine: {exc}"}

    # La API CDX devuelve la primera fila como encabezado de columnas
    # (["original", "timestamp"]), no como un snapshot real.
    if not rows or len(rows) <= 1:
        return {"snapshots": [], "total": 0}

    data_rows = rows[1:]
    snapshots = [{"url": row[0], "timestamp": row[1]} for row in data_rows]

    return {"snapshots": snapshots, "total": len(snapshots)}
