"""
Módulo de emails: busca direcciones de correo asociadas a un dominio.

No existe una "API de emails": este módulo combina varias fuentes de
datos públicas que ya usamos en otros módulos, buscando en todo ese
texto un patrón (regex) que parezca una dirección de correo:

  - WHOIS: algunos registradores exponen el email de contacto del dominio.
  - DNS TXT del dominio y de "_dmarc.<dominio>": los registros DMARC
    suelen incluir "rua=mailto:..." / "ruf=mailto:..." con la dirección
    donde el dominio quiere recibir reportes de autenticación de correo.
  - La página principal del sitio (HTML): a veces el email de contacto
    está escrito directamente en el pie de página o en un mailto:.
"""
import re

import httpx

from . import dns_module, whois_module

EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
HTTP_TIMEOUT_SECONDS = 10


def _extract_emails(text: str | None) -> set[str]:
    """Devuelve el conjunto de direcciones de correo encontradas en un texto."""
    if not text:
        return set()
    return {match.lower() for match in EMAIL_REGEX.findall(text)}


def _emails_from_whois(target: str) -> set[str]:
    data = whois_module.run(target)
    emails_field = data.get("emails")
    if not emails_field:
        return set()
    if isinstance(emails_field, str):
        return {emails_field.lower()}
    return {str(e).lower() for e in emails_field}


def _emails_from_dns_txt(target: str) -> set[str]:
    """Busca emails en los TXT del dominio y en los de _dmarc.<dominio>."""
    emails: set[str] = set()
    for query_name in (target, f"_dmarc.{target}"):
        dns_data = dns_module.run(query_name)
        for record in dns_data.get("TXT", []):
            emails |= _extract_emails(record)
    return emails


def _emails_from_homepage(target: str) -> set[str]:
    """Descarga la página principal (probando HTTPS y luego HTTP) y busca emails en el HTML."""
    for scheme in ("https", "http"):
        url = f"{scheme}://{target}"
        try:
            response = httpx.get(url, timeout=HTTP_TIMEOUT_SECONDS, follow_redirects=True)
            return _extract_emails(response.text)
        except Exception:
            continue  # probamos el siguiente esquema (o nos quedamos sin datos de esta fuente)
    return set()


def _belongs_to_domain(email: str, domain: str) -> bool:
    """True si el email es de `domain` o de un subdominio suyo."""
    email_domain = email.rsplit("@", 1)[-1]
    return email_domain == domain or email_domain.endswith("." + domain)


def run(target: str) -> dict:
    """
    Busca emails relacionados con `target` combinando WHOIS, DNS (TXT y
    DMARC) y el contenido de la página principal del sitio.
    """
    whois_emails = _emails_from_whois(target)
    dns_emails = _emails_from_dns_txt(target)
    homepage_emails = _emails_from_homepage(target)

    all_emails = whois_emails | dns_emails | homepage_emails
    domain_emails = sorted(e for e in all_emails if _belongs_to_domain(e, target))
    other_emails = sorted(all_emails - set(domain_emails))

    return {
        "domain_emails": domain_emails,
        "other_emails": other_emails,
        "total": len(all_emails),
        "sources": {
            "whois": sorted(whois_emails),
            "dns_txt": sorted(dns_emails),
            "homepage": sorted(homepage_emails),
        },
    }
