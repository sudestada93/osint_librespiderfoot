"""
Módulo SSL/TLS: extrae el certificado y su metadata de un servidor.

Cuando un cliente (navegador, o este módulo) se conecta a un servidor por
HTTPS, el servidor le presenta un certificado digital que prueba su
identidad y define hasta cuándo es válido. Acá hacemos ese mismo
"saludo" (handshake TLS) para leer esos datos directamente, sin usar un
navegador.

A propósito NO validamos la cadena de confianza del certificado (como sí
hace un navegador): para reconocimiento nos interesa ver el certificado
tal cual lo presenta el servidor, incluso si es autofirmado, está vencido
o no coincide con el hostname -- eso también es un hallazgo útil.

Nota técnica: cuando se desactiva la verificación, el módulo estándar
`ssl` de Python deja de parsear el certificado (`getpeercert()` devuelve
vacío). Por eso pedimos el certificado en formato binario (DER) y lo
parseamos nosotros mismos con la librería `cryptography`.
"""
import socket
import ssl
from datetime import datetime, timezone

from cryptography import x509
from cryptography.x509.oid import NameOID

DEFAULT_PORT = 443
TIMEOUT_SECONDS = 8


def _get_name_attribute(name: x509.Name, oid) -> str | None:
    """Devuelve el primer valor de un atributo (ej: CommonName) de un subject/issuer."""
    attributes = name.get_attributes_for_oid(oid)
    return attributes[0].value if attributes else None


def run(target: str, port: int = DEFAULT_PORT) -> dict:
    """
    Se conecta a target:port por TLS y devuelve los datos del certificado
    presentado: titular, emisor, validez, nombres alternativos, etc.
    """
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False  # tiene que ir antes de tocar verify_mode
    context.verify_mode = ssl.CERT_NONE

    try:
        with socket.create_connection((target, port), timeout=TIMEOUT_SECONDS) as sock:
            with context.wrap_socket(sock, server_hostname=target) as tls_sock:
                der_cert = tls_sock.getpeercert(binary_form=True)
                cipher = tls_sock.cipher()
                tls_version = tls_sock.version()
    except Exception as exc:
        return {"error": f"No se pudo conectar por TLS a {target}:{port}: {exc}"}

    if not der_cert:
        return {"error": f"El servidor no presentó un certificado en {target}:{port}"}

    cert = x509.load_der_x509_certificate(der_cert)

    subject_cn = _get_name_attribute(cert.subject, NameOID.COMMON_NAME)
    issuer_cn = _get_name_attribute(cert.issuer, NameOID.COMMON_NAME)
    issuer_org = _get_name_attribute(cert.issuer, NameOID.ORGANIZATION_NAME)

    try:
        san_extension = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        subject_alt_names = san_extension.value.get_values_for_type(x509.DNSName)
    except x509.ExtensionNotFound:
        subject_alt_names = []

    valid_from = cert.not_valid_before_utc
    valid_until = cert.not_valid_after_utc
    now = datetime.now(timezone.utc)

    return {
        "subject_common_name": subject_cn,
        "issuer_common_name": issuer_cn,
        "issuer_organization": issuer_org,
        "valid_from": valid_from.isoformat(),
        "valid_until": valid_until.isoformat(),
        "currently_valid": valid_from <= now <= valid_until,
        "days_until_expiry": (valid_until - now).days,
        "serial_number": format(cert.serial_number, "x"),
        "subject_alt_names": list(subject_alt_names),
        "tls_version": tls_version,
        "cipher_suite": cipher[0] if cipher else None,
    }
