"""
Módulo de lookup de teléfono: valida y extrae información pública de un
número usando `phonenumbers` (el port a Python de libphonenumber, la
misma librería que usan Android/Google). Funciona 100% OFFLINE: los
datos de país, operador y huso horario vienen embebidos en la propia
librería, sin ninguna llamada de red ni API key.
"""
import phonenumbers
from phonenumbers import carrier as phonenumbers_carrier
from phonenumbers import geocoder as phonenumbers_geocoder
from phonenumbers import timezone as phonenumbers_timezone

NUMBER_TYPE_NAMES = {
    phonenumbers.PhoneNumberType.FIXED_LINE: "línea fija",
    phonenumbers.PhoneNumberType.MOBILE: "celular",
    phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE: "línea fija o celular",
    phonenumbers.PhoneNumberType.TOLL_FREE: "número gratuito",
    phonenumbers.PhoneNumberType.PREMIUM_RATE: "tarifa premium",
    phonenumbers.PhoneNumberType.SHARED_COST: "costo compartido",
    phonenumbers.PhoneNumberType.VOIP: "VoIP",
    phonenumbers.PhoneNumberType.PERSONAL_NUMBER: "número personal",
    phonenumbers.PhoneNumberType.PAGER: "pager",
    phonenumbers.PhoneNumberType.UAN: "UAN (acceso universal)",
    phonenumbers.PhoneNumberType.UNKNOWN: "desconocido",
}

# Región por defecto para interpretar números que vienen SIN código de
# país (sin el "+"). Si el usuario escribe el número completo con "+"
# (ej: +5491122334455), este valor no se usa para nada.
DEFAULT_REGION = "US"


def run(phone: str, default_region: str = DEFAULT_REGION) -> dict:
    """Analiza `phone`: validez, formato, país, operador, tipo de línea y husos horarios."""
    try:
        parsed = phonenumbers.parse(phone, default_region)
    except phonenumbers.NumberParseException as exc:
        return {"error": f"No se pudo interpretar '{phone}' como un teléfono: {exc}"}

    if not phonenumbers.is_valid_number(parsed):
        return {"error": f"'{phone}' no es un número de teléfono válido"}

    number_type = phonenumbers.number_type(parsed)

    return {
        "e164": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164),
        "international": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.INTERNATIONAL),
        "national": phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.NATIONAL),
        "country_code": parsed.country_code,
        "region": phonenumbers_geocoder.description_for_number(parsed, "es") or None,
        "carrier": phonenumbers_carrier.name_for_number(parsed, "es") or None,
        "line_type": NUMBER_TYPE_NAMES.get(number_type, "desconocido"),
        "possible_timezones": list(phonenumbers_timezone.time_zones_for_number(parsed)),
    }
