"""
Punto de entrada de MiniSpider.

Acá se crea la aplicación de FastAPI, se sirve el frontend y se exponen
dos tipos de endpoints:

  - GET /api/scan/<modulo>: corre UN módulo puntual contra un target
    (útil para probar un módulo aislado, o para una consulta rápida).
  - POST /api/scan: corre VARIOS módulos en paralelo (orquestador),
    guarda el resultado en SQLite y lo devuelve. Este es el que usa el
    formulario principal del frontend.
  - GET /api/scans, /api/scans/{id}, /api/scans/{id}/export: consultar
    el historial de scans guardados y exportarlos a JSON/CSV.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .core import database, export, orchestrator
from .models.scan import ScanRequest
from .modules import (
    dns_module,
    emails_module,
    geoip_module,
    headers_module,
    ports_module,
    robots_module,
    ssl_module,
    subdomains_module,
    wayback_module,
    whois_module,
)

# BASE_DIR apunta siempre a la carpeta raíz del proyecto (mini-spider/),
# sin importar desde qué directorio se ejecute el comando "uvicorn".
BASE_DIR = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Se ejecuta una sola vez, al arrancar el servidor: crea la tabla de
    # la base de datos si todavía no existe.
    database.init_db()
    yield


# Instancia principal de la aplicación. FastAPI usa esta metadata para
# generar automáticamente documentación interactiva en /docs.
app = FastAPI(
    title="MiniSpider",
    description="Herramienta OSINT open-source para reconocimiento pasivo.",
    version="0.1.0",
    lifespan=lifespan,
)

# Sirve archivos estáticos (CSS, JS del frontend) bajo la ruta /static/...
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "frontend" / "static")), name="static")

# Jinja2Templates permite renderizar archivos .html pasándoles variables
# de Python (por ejemplo, el nombre de la app o los resultados de un scan).
templates = Jinja2Templates(directory=str(BASE_DIR / "frontend" / "templates"))


@app.get("/api/ping")
def ping():
    """Endpoint simple en formato JSON para verificar que el backend responde."""
    return {"status": "ok", "message": "MiniSpider backend funcionando"}


@app.get("/api/modules")
def list_modules():
    """Devuelve los módulos disponibles, para que el frontend arme los checkboxes dinámicamente."""
    return {"modules": orchestrator.ALL_MODULE_NAMES, "default_modules": orchestrator.DEFAULT_MODULES}


# --- Endpoints de un solo módulo (útiles para pruebas puntuales) -----------

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


@app.get("/api/scan/ssl")
def scan_ssl(
    target: str = Query(..., description="Host o dominio a consultar"),
    port: int = Query(443, gt=0, le=65535, description="Puerto TLS, por defecto 443"),
):
    """Ejecuta el módulo SSL/TLS: extrae el certificado presentado por target:port."""
    target = target.strip().lower()
    return {"target": target, "module": "ssl", "results": ssl_module.run(target, port=port)}


@app.get("/api/scan/emails")
def scan_emails(target: str = Query(..., description="Dominio a buscar, ej: example.com")):
    """Busca emails asociados al dominio combinando WHOIS, DNS y la página principal."""
    target = target.strip().lower()
    return {"target": target, "module": "emails", "results": emails_module.run(target)}


@app.get("/api/scan/geoip")
def scan_geoip(target: str = Query(..., description="IP o dominio a geolocalizar")):
    """Geolocaliza target (IP o dominio, resuelto vía DNS) usando ip-api.com."""
    target = target.strip().lower()
    return {"target": target, "module": "geoip", "results": geoip_module.run(target)}


@app.get("/api/scan/headers")
def scan_headers(target: str = Query(..., description="Dominio o host a consultar")):
    """Descarga la página principal de target y analiza sus headers HTTP."""
    target = target.strip().lower()
    return {"target": target, "module": "headers", "results": headers_module.run(target)}


@app.get("/api/scan/robots")
def scan_robots(target: str = Query(..., description="Dominio o host a consultar")):
    """Busca y parsea robots.txt y sitemap.xml de target."""
    target = target.strip().lower()
    return {"target": target, "module": "robots", "results": robots_module.run(target)}


@app.get("/api/scan/wayback")
def scan_wayback(target: str = Query(..., description="Dominio o host a consultar")):
    """Busca snapshots históricos de target en Wayback Machine."""
    target = target.strip().lower()
    return {"target": target, "module": "wayback", "results": wayback_module.run(target)}


# --- Scan completo (orquestador) + historial persistido en SQLite ---------

@app.post("/api/scan")
async def create_scan(payload: ScanRequest):
    """
    Corre varios módulos en paralelo contra payload.target, guarda el
    resultado en la base de datos y lo devuelve.
    """
    target = payload.target.strip().lower()
    module_kwargs = {
        "ports": {
            "ports_spec": payload.ports,
            "timeout": payload.ports_timeout,
            "concurrency": payload.ports_concurrency,
        },
        "ssl": {"port": payload.ssl_port},
    }

    try:
        results = await orchestrator.run_scan(target, modules=payload.modules, module_kwargs=module_kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    modules_used = payload.modules if payload.modules is not None else orchestrator.DEFAULT_MODULES
    scan_id = database.save_scan(target, modules_used, results)

    return {"scan_id": scan_id, "target": target, "modules": modules_used, "results": results}


@app.get("/api/scans")
def get_scans():
    """Devuelve el historial de scans guardados (resumen, sin los resultados completos)."""
    return database.list_scans()


@app.get("/api/scans/{scan_id}")
def get_scan_detail(scan_id: int):
    """Devuelve un scan guardado, con todos sus resultados."""
    scan = database.get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail=f"No existe un scan con id {scan_id}")
    return scan


@app.get("/api/scans/{scan_id}/export")
def export_scan(
    scan_id: int,
    format: str = Query("json", pattern="^(json|csv)$", description="Formato de exportación: json o csv"),
):
    """Descarga un scan guardado como archivo JSON o CSV."""
    scan = database.get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail=f"No existe un scan con id {scan_id}")

    if format == "csv":
        content = export.scan_to_csv(scan)
        media_type = "text/csv"
        filename = f"minispider_scan_{scan_id}.csv"
    else:
        import json

        content = json.dumps(scan, indent=2, ensure_ascii=False)
        media_type = "application/json"
        filename = f"minispider_scan_{scan_id}.json"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/")
def home(request: Request):
    """Página principal: formulario de escaneo, resultados e historial."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"app_name": "MiniSpider"},
    )
