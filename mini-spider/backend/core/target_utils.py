"""
Detección del tipo de objetivo a partir del texto que escribe el usuario.

MiniSpider acepta un único campo de texto libre ("target"): acá decidimos
si lo que escribió es un dominio, una IP, un email, un teléfono o un
username, para poder mostrar/correr solo los módulos que tienen sentido
para ese tipo (no tiene sentido correr WHOIS sobre un email, por ejemplo).

Es una heurística simple, no un parser perfecto: prioriza los formatos
más específicos (email, IP, teléfono) antes de caer en dominio o, como
último recurso, username.
"""
import re

EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
IPV4_REGEX = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
DOMAIN_REGEX = re.compile(r"^(?=.{1,253}$)[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$")
# Un teléfono: solo dígitos, espacios, guiones, paréntesis y un "+" opcional
# al principio, con al menos 7 dígitos (para no confundirlo con un id corto).
PHONE_REGEX = re.compile(r"^\+?[\d\s().-]{7,20}$")

TARGET_TYPES = ("email", "ip", "phone", "domain", "username")


def detect_target_type(target: str) -> str:
    """Devuelve uno de TARGET_TYPES según el formato de `target`."""
    target = target.strip()

    if EMAIL_REGEX.match(target):
        return "email"
    if IPV4_REGEX.match(target):
        return "ip"
    if PHONE_REGEX.match(target) and sum(c.isdigit() for c in target) >= 7:
        return "phone"
    if DOMAIN_REGEX.match(target):
        return "domain"
    return "username"
