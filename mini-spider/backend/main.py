"""
Punto de entrada de MiniSpider.

Acá se crea la aplicación de FastAPI (el "servidor web" que va a recibir
peticiones del navegador) y se definen las primeras rutas de prueba.
Los módulos de reconocimiento (DNS, WHOIS, etc.) se van a ir conectando
en fases siguientes.
"""
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates

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


@app.get("/")
def home(request: Request):
    """Página principal. Por ahora solo muestra un saludo de bienvenida."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"app_name": "MiniSpider"},
    )
