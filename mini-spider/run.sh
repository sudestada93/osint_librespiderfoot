#!/bin/bash
# Script de arranque de MiniSpider.
# Activa el entorno virtual y levanta el servidor de desarrollo con recarga
# automática (los cambios en el código se reflejan sin reiniciar a mano).

set -e  # Si algún comando falla, el script se detiene en vez de seguir a ciegas.

# Nos posicionamos en la carpeta donde está este script (mini-spider/),
# sin importar desde qué directorio lo hayas ejecutado.
cd "$(dirname "$0")"

# Si todavía no creaste el entorno virtual, avisamos con instrucciones claras
# en vez de fallar con un error críptico.
if [ ! -d "venv" ]; then
    echo "No se encontró el entorno virtual 'venv'. Corré primero:"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

source venv/bin/activate

echo "Iniciando MiniSpider en http://localhost:8000 ..."
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
