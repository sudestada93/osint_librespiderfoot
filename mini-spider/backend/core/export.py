"""
Exportación de resultados de un scan a CSV.

Los resultados de cada módulo tienen una forma distinta (listas, dicts
anidados, valores sueltos), así que para armar un CSV --que es tabular
por naturaleza-- aplanamos cada resultado a filas de (módulo, campo, valor).
"""
import csv
import io


def _flatten(prefix: str, value, rows: list[tuple[str, str]]) -> None:
    """Recorre `value` recursivamente y va agregando pares (ruta_completa, valor_texto) a `rows`."""
    if isinstance(value, dict):
        for key, sub_value in value.items():
            _flatten(f"{prefix}.{key}", sub_value, rows)
    elif isinstance(value, list):
        if not value:
            rows.append((prefix, "[]"))
        for index, item in enumerate(value):
            _flatten(f"{prefix}[{index}]", item, rows)
    else:
        rows.append((prefix, "" if value is None else str(value)))


def scan_to_csv(scan: dict) -> str:
    """Convierte un scan (con su campo "results") a un CSV en texto, con columnas module, field, value."""
    rows: list[tuple[str, str]] = []
    for module_name, module_result in scan["results"].items():
        _flatten(module_name, module_result, rows)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["module", "field", "value"])
    for path, text_value in rows:
        module, _, field = path.partition(".")
        writer.writerow([module, field, text_value])
    return buffer.getvalue()
