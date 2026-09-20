"""
Módulo DNS: resuelve los registros más comunes de un dominio.

DNS (Domain Name System) es el sistema que traduce nombres de dominio
("ejemplo.com") a direcciones IP y otra información asociada. Este módulo
consulta distintos "tipos de registro" para armar un perfil básico del
dominio objetivo, todo con datos públicos (no requiere ninguna API key).
"""
import dns.resolver

# Tipos de registro que vamos a consultar. Cada uno cuenta algo distinto:
# A     -> dirección IPv4 del dominio
# AAAA  -> dirección IPv6 del dominio
# MX    -> servidores que reciben el correo de ese dominio
# TXT   -> texto libre (a veces incluye verificaciones SPF/DKIM, o dueños)
# NS    -> servidores de nombres autoritativos (quién resuelve el dominio)
# CNAME -> alias hacia otro dominio
RECORD_TYPES = ["A", "AAAA", "MX", "TXT", "NS", "CNAME"]


def run(target: str) -> dict:
    """
    Consulta los registros DNS de `target` y devuelve un diccionario
    {tipo_de_registro: [valores]}. Si el dominio no existe, devuelve
    directamente la clave "error".
    """
    resolver = dns.resolver.Resolver()
    resolver.timeout = 5   # segundos que espera una respuesta individual
    resolver.lifetime = 5  # segundos totales por consulta (incluye reintentos)

    results = {}

    for record_type in RECORD_TYPES:
        try:
            answers = resolver.resolve(target, record_type)
            # Convertimos cada respuesta a texto simple para poder
            # devolverla como JSON sin problemas.
            results[record_type] = [str(answer) for answer in answers]
        except dns.resolver.NXDOMAIN:
            # El dominio directamente no existe: no tiene sentido seguir
            # probando los demás tipos de registro.
            return {"error": f"El dominio '{target}' no existe (NXDOMAIN)"}
        except dns.resolver.NoAnswer:
            # El dominio existe pero no tiene registros de este tipo.
            results[record_type] = []
        except dns.exception.Timeout:
            results[record_type] = []
        except Exception:
            # Cualquier otro error de resolución (servidor no disponible, etc.)
            results[record_type] = []

    return results
