"""
Módulo de escaneo de puertos: TCP connect scan usando sockets asíncronos.

Un "puerto" es un número (1-65535) que identifica un servicio que corre
en un host (por ejemplo, el 80 suele ser HTTP, el 22 SSH). Este módulo
intenta abrir una conexión TCP a cada puerto del rango indicado; si la
conexión se establece, el puerto está "abierto" (hay algo escuchando).

A diferencia de los módulos anteriores (DNS, WHOIS, crt.sh), esto es un
escaneo ACTIVO: genera tráfico real contra el objetivo. Usalo solo
contra hosts propios o con autorización explícita.

No hay una lista fija de puertos "permitidos": se puede pedir un puerto
puntual, una lista, un rango, o "all" para los 65535 puertos.
"""
import asyncio

# Lista por defecto si no se especifica nada en `ports_spec` (no es una
# limitación: el caller puede pedir "all" o cualquier rango propio).
COMMON_PORTS = [
    21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445,
    993, 995, 1723, 3306, 3389, 5432, 5900, 6379, 8000, 8080, 8443, 27017,
]

DEFAULT_TIMEOUT_SECONDS = 1.5
DEFAULT_CONCURRENCY = 500  # conexiones simultáneas máximas


def parse_ports(spec: str | None) -> list[int]:
    """
    Convierte el parámetro `ports` (texto) en una lista de números de puerto.

    Formatos aceptados:
      - None o vacío   -> COMMON_PORTS (valor por defecto)
      - "all"          -> todos los puertos, 1-65535
      - "80,443,8080"  -> lista explícita
      - "1-1024"       -> rango
      - "22,80,1000-2000" -> combinación de listas y rangos

    Lanza ValueError si el texto no se puede interpretar como puertos.
    """
    if spec is None or not spec.strip():
        return list(COMMON_PORTS)

    if spec.strip().lower() == "all":
        return list(range(1, 65536))

    ports: set[int] = set()
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "-" in chunk:
            start_str, end_str = chunk.split("-", 1)
            start, end = int(start_str), int(end_str)
            if start > end:
                start, end = end, start
            ports.update(range(start, end + 1))
        else:
            ports.add(int(chunk))

    # Descartamos cualquier valor fuera del rango válido de puertos TCP.
    return sorted(p for p in ports if 0 < p <= 65535)


async def _check_port(host: str, port: int, timeout: float, semaphore: asyncio.Semaphore) -> bool:
    """Intenta abrir una conexión TCP al puerto. Devuelve True si se pudo conectar."""
    async with semaphore:
        try:
            _reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=timeout
            )
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass  # el cierre prolijo es "nice to have", no crítico
            return True
        except Exception:
            # Cubre: ConnectionRefusedError (puerto cerrado), TimeoutError
            # (puerto filtrado / firewall), y errores de resolución de host.
            return False


async def run(
    target: str,
    ports_spec: str | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> dict:
    """
    Escanea `target` en los puertos indicados por `ports_spec` y devuelve
    cuáles están abiertos. El escaneo se hace en paralelo (hasta
    `concurrency` conexiones simultáneas) para que rangos grandes o "all"
    sean viables en tiempo razonable.
    """
    try:
        ports = parse_ports(ports_spec)
    except ValueError:
        return {"error": f"Formato de puertos inválido: '{ports_spec}'"}

    if not ports:
        return {"error": "No se especificó ningún puerto válido"}

    semaphore = asyncio.Semaphore(max(1, concurrency))
    tasks = [_check_port(target, port, timeout, semaphore) for port in ports]
    is_open_list = await asyncio.gather(*tasks)

    open_ports = sorted(port for port, is_open in zip(ports, is_open_list) if is_open)

    return {
        "scanned": len(ports),
        "open_ports": open_ports,
        "total_open": len(open_ports),
    }
