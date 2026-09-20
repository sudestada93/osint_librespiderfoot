"""
Persistencia de resultados de scans en SQLite.

Elegimos SQLite (en vez de Postgres/MySQL) porque no requiere instalar
ni configurar un servidor de base de datos aparte: es un único archivo
en disco (`data/minispider.db`), ideal para una herramienta que corre
en la máquina de un solo usuario.
"""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "minispider.db"


def _get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Crea la tabla `scans` si todavía no existe. Se llama al arrancar la app."""
    with _get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target TEXT NOT NULL,
                modules TEXT NOT NULL,
                created_at TEXT NOT NULL,
                results_json TEXT NOT NULL
            )
            """
        )


def save_scan(target: str, modules: list[str], results: dict) -> int:
    """Guarda un scan completo y devuelve el id autogenerado."""
    with _get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO scans (target, modules, created_at, results_json) VALUES (?, ?, ?, ?)",
            (target, json.dumps(modules), datetime.now(timezone.utc).isoformat(), json.dumps(results)),
        )
        return cursor.lastrowid


def list_scans() -> list[dict]:
    """Resumen (sin los resultados completos, para que la lista sea liviana) de todos los scans, más reciente primero."""
    with _get_connection() as conn:
        rows = conn.execute(
            "SELECT id, target, modules, created_at FROM scans ORDER BY id DESC"
        ).fetchall()
    return [
        {
            "id": row["id"],
            "target": row["target"],
            "modules": json.loads(row["modules"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def get_scan(scan_id: int) -> dict | None:
    """Devuelve un scan completo (con resultados) por id, o None si no existe."""
    with _get_connection() as conn:
        row = conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "target": row["target"],
        "modules": json.loads(row["modules"]),
        "created_at": row["created_at"],
        "results": json.loads(row["results_json"]),
    }
