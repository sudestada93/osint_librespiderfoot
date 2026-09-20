"""
Punto de entrada de MiniSpider.

Acá se crea la aplicación de FastAPI (el "servidor web" que va a recibir
peticiones del navegador) y se definen las primeras rutas de prueba.
Los módulos de reconocimiento (DNS, WHOIS, etc.) se van a ir conectando
en fases siguientes.
"""
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.templating import Jinja2Templates

from .modules import dns_module, ports_module, subdomains_module, whois_module

# BASE_DIR apunta siempre a la carpeta raíz del proyecto (mini-spider/),
# sin importar desde qué directorio se ejecute el comando "uvicorn".
BASE_DIR = Path(__file__).resolve().parent.parent

# Instancia principal de la aplicación. FastAPI usa esta metadata para
# generar automáticamente documentación interactiva en /docs.
app = FastAPI(
    title="MiniSpider",
    description="Herramienta OSINT open-source para reconocimiento pasivo.",
    version="0.1.0",
)

# Jinja2Templates permite renderizar archivos .html pasándoles variables
# de Python (por ejemplo, el nombre de la app o los resultados de un scan).
templates = Jinja2Templates(directory=str(BASE_DIR / "frontend" / "templates"))


@app.get("/api/ping")
def ping():
    """Endpoint simple en formato JSON para verificar que el backend responde."""
    return {"status": "ok", "message": "MiniSpider backend funcionando"}


@app.get("/api/scan/dns")
def scan_dns(target: str = Query(..., description="Dominio a resolver, ej: example.com")):
    """Ejecuta el módulo DNS sobre el dominio indicado y devuelve sus registros."""
    target = target.strip().lower()
    return {"target": target, "module": "dns", "results": dns_module.run(target)}


@app.get("/api/scan/whois")
def scan_whois(target: str = Query(..., description="Dominio a consultar, ej: example.com")):
    """Ejecuta el módulo WHOIS sobre el dominio indicado."""
    target = target.strip().lower()
    return {"target": target, "module": "whois", "results": whois_module.run(target)}


@app.get("/api/scan/subdomains")
def scan_subdomains(target: str = Query(..., description="Dominio a buscar, ej: example.com")):
    """Ejecuta el módulo de subdominios (crt.sh) sobre el dominio indicado."""
    target = target.strip().lower()
    return {"target": target, "module": "subdomains", "results": subdomains_module.run(target)}


@app.get("/api/scan/ports")
async def scan_ports(
    target: str = Query(..., description="Host o IP a escanear"),
    ports: str | None = Query(
        None,
        description=(
            "Puertos a escanear: 'all' (1-65535), lista '80,443,8080', "
            "rango '1-1024', o combinación '22,80,1000-2000'. "
            "Si se omite, usa una lista de puertos comunes."
        ),
    ),
    timeout: float = Query(1.5, gt=0, description="Timeout por puerto, en segundos"),
    concurrency: int = Query(500, gt=0, le=5000, description="Conexiones simultáneas máximas"),
):
    """
    Ejecuta un escaneo TCP connect scan sobre `target`.

    ADVERTENCIA: esto genera tráfico real contra el host indicado.
    Usalo solo contra hosts propios o con autorización explícita.
    """
    target = target.strip().lower()
    result = await ports_module.run(target, ports_spec=ports, timeout=timeout, concurrency=concurrency)
    return {"target": target, "module": "ports", "results": result}


@app.get("/")
def home(request: Request):
    """Página principal. Por ahora solo muestra un saludo de bienvenida."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"app_name": "MiniSpider"},
    )
