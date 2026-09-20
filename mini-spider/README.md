# MiniSpider

Herramienta OSINT (*Open Source Intelligence*) gratuita y de código abierto para reconocimiento pasivo (y un módulo activo, claramente marcado) de dominios, IPs y hosts. Corre 100% en local, sin necesidad de ninguna API key de pago.

## ⚠️ Disclaimer legal y ético

**Usá esta herramienta únicamente contra objetivos propios, o con autorización explícita y por escrito del dueño del sistema.** Varios módulos (en especial el escaneo de puertos) generan tráfico activo contra el objetivo. Escanear sistemas ajenos sin permiso puede ser ilegal en tu país, incluso si la intención es "solo mirar". El autor de esta herramienta no se hace responsable del uso que se le dé.

## Qué hace

MiniSpider recibe un objetivo (dominio, IP o host) y corre en paralelo hasta 10 módulos de reconocimiento:

| Módulo | Qué hace | Tipo |
|---|---|---|
| `dns` | Resuelve registros A, AAAA, MX, TXT, NS, CNAME | Pasivo |
| `whois` | Datos de registro del dominio (registrador, fechas, contacto) | Pasivo |
| `subdomains` | Enumera subdominios vía Certificate Transparency (crt.sh) | Pasivo |
| `ssl` | Extrae el certificado SSL/TLS presentado por el host | Pasivo* |
| `emails` | Busca emails en WHOIS, DNS (TXT/DMARC) y la página principal | Pasivo |
| `geoip` | Geolocaliza una IP (o el dominio resuelto) con ip-api.com | Pasivo |
| `headers` | Analiza headers HTTP y detecta pistas de tecnologías | Pasivo* |
| `robots` | Descarga y parsea robots.txt y sitemap.xml | Pasivo* |
| `wayback` | Busca URLs históricas archivadas en Wayback Machine | Pasivo |
| `ports` | Escaneo TCP connect scan (puertos custom, o "all") | **Activo** |

\* Técnicamente hacen una conexión al objetivo (como cualquier visita normal a un sitio web), pero no son intrusivos ni intentan explotar nada.

Los resultados se guardan en una base de datos SQLite local, se pueden ver en el navegador, y se pueden exportar a JSON o CSV.

## Stack técnico

- **Backend**: Python 3.11+ con FastAPI
- **Frontend**: HTML + CSS + JavaScript vanilla (sin frameworks ni build tools)
- **Base de datos**: SQLite (un único archivo, sin servidor que instalar)
- **Concurrencia**: `asyncio` para correr todos los módulos en paralelo

## Requisitos

- Linux (probado en Debian/Ubuntu; en Fedora/Arch los comandos de instalación de paquetes cambian, ver abajo)
- Python 3.10 o superior
- Conexión a internet (para los módulos que consultan fuentes externas)

## Instalación

```bash
# 1. Verificá que tenés Python 3 y el módulo venv
python3 --version

# Si falta python3-venv (Debian/Ubuntu):
sudo apt update && sudo apt install -y python3-venv python3-pip
# Fedora:
#   sudo dnf install python3-pip
# Arch:
#   sudo pacman -S python-pip

# 2. Cloná el repo y entrá a la carpeta del proyecto
git clone <url-de-tu-repo>
cd osint_librespiderfoot/mini-spider

# 3. Creá y activá el entorno virtual
python3 -m venv venv
source venv/bin/activate

# 4. Instalá las dependencias
pip install --upgrade pip
pip install -r requirements.txt
```

## Uso

```bash
./run.sh
```

Esto levanta el servidor en `http://localhost:8000`. Abrí esa URL en tu navegador:

1. Escribí un objetivo (dominio, IP o host) en el campo de texto.
2. Tildá los módulos que querés correr (por defecto vienen tildados todos menos `ports`, que es el único activo).
3. Si tildás `ports`, podés indicar qué puertos escanear (vacío = lista común, `all` = los 65535, o un rango como `1-1024`).
4. Hacé clic en "Escanear". Los resultados aparecen por módulo, cada uno colapsable.
5. Todos los scans quedan guardados en el historial, con links para exportar a JSON o CSV.

### Uso por API (sin el navegador)

```bash
# Un módulo puntual
curl "http://localhost:8000/api/scan/dns?target=example.com"

# Scan completo (todos los módulos por defecto)
curl -X POST http://localhost:8000/api/scan \
  -H "Content-Type: application/json" \
  -d '{"target": "example.com"}'

# Scan con módulos específicos
curl -X POST http://localhost:8000/api/scan \
  -H "Content-Type: application/json" \
  -d '{"target": "example.com", "modules": ["dns", "ssl", "headers"]}'

# Historial y exportación
curl http://localhost:8000/api/scans
curl "http://localhost:8000/api/scans/1/export?format=csv" -o scan.csv
```

La documentación interactiva completa de la API está en `http://localhost:8000/docs` (generada automáticamente por FastAPI).

## Estructura del proyecto

```
mini-spider/
├── backend/
│   ├── main.py              # App FastAPI, endpoints
│   ├── core/
│   │   ├── orchestrator.py  # Corre módulos en paralelo
│   │   ├── database.py      # Persistencia SQLite
│   │   └── export.py        # Exportación a CSV
│   ├── models/
│   │   └── scan.py          # Modelo Pydantic del request de scan
│   └── modules/              # Un archivo por módulo de reconocimiento
├── frontend/
│   ├── templates/index.html
│   └── static/{style.css,app.js}
├── data/                     # Acá vive minispider.db (no se versiona)
├── requirements.txt
├── run.sh
└── README.md
```

## Errores comunes

- **`ModuleNotFoundError`** → olvidaste activar el entorno virtual (`source venv/bin/activate`) antes de instalar o correr.
- **`bash: ./run.sh: Permission denied`** → `chmod +x run.sh`.
- **`Address already in use`** → ya hay algo corriendo en el puerto 8000. Buscalo con `sudo lsof -i :8000` y matalo, o cambiá el puerto en `run.sh`.
- **Un módulo siempre devuelve `{"error": "..."}`** → puede ser normal (dominio sin WHOIS público, sin DMARC, sin sitemap) o tu red puede estar bloqueando ese tipo de tráfico (algunas redes corporativas bloquean el puerto 43 de WHOIS, por ejemplo).
- **El escaneo de puertos tarda mucho** → si pediste `ports=all` contra un host que no responde nada (firewall que descarta paquetes en silencio), cada puerto espera el timeout completo. Bajá `timeout` o subí `concurrency` en el form/API.
- **`Too many open files` al escanear muchos puertos** → subí el límite con `ulimit -n 4096` antes de correr `run.sh`, o bajá la concurrencia.

## Licencia y filosofía

100% gratis y de código abierto. Ninguna dependencia requiere una API key de pago; los servicios externos que usa (crt.sh, ip-api.com, Wayback Machine) tienen planes gratuitos suficientes para uso personal.
