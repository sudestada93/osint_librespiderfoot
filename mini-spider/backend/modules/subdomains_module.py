"""
Módulo de subdominios: enumeración pasiva vía Certificate Transparency (crt.sh).

Cuando se emite un certificado SSL/TLS para un dominio, ese hecho queda
registrado públicamente en los "Certificate Transparency logs" (un
requisito de seguridad que exigen los navegadores modernos). El sitio
crt.sh indexa esos logs y permite buscar todos los certificados emitidos
para un dominio y sus subdominios.

Es una técnica "pasiva": no le mandamos ningún tráfico al servidor del
objetivo, solo consultamos un registro público de terceros.
"""
import httpx

CRTSH_URL = "https://crt.sh/"
TIMEOUT_SECONDS = 15


def run(target: str) -> dict:
    """
    Busca en crt.sh los certificados emitidos para *.target (y target)
    y devuelve la lista de subdominios únicos encontrados, ordenada.
    """
    params = {"q": f"%.{target}", "output": "json"}

    try:
        response = httpx.get(CRTSH_URL, params=params, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        return {"error": f"No se pudo consultar crt.sh: {exc}"}

    try:
        entries = response.json()
    except ValueError:
        # crt.sh a veces devuelve una respuesta vacía (no JSON) si no hay
        # ningún certificado registrado para ese dominio.
        return {"subdomains": [], "total": 0}

    subdomains = set()
    for entry in entries:
        # Un mismo certificado puede cubrir varios nombres (SAN), separados
        # por saltos de línea dentro del campo "name_value".
        name_value = entry.get("name_value", "")
        for name in name_value.split("\n"):
            # Los certificados wildcard aparecen como "*.sub.dominio.com";
            # nos quedamos con el nombre real sin el "*."
            name = name.strip().lstrip("*.").lower()
            if name and target in name:
                subdomains.add(name)

    return {"subdomains": sorted(subdomains), "total": len(subdomains)}
