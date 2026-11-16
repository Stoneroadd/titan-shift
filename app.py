"""Small, dependency-free mining shift KPI demo using synthetic inputs."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from datetime import date
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get("TITAN_DB_PATH", ROOT / "titan_shift.sqlite3"))


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("""
        CREATE TABLE IF NOT EXISTS shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shift_date TEXT NOT NULL,
            name TEXT NOT NULL,
            planned_tonnes REAL NOT NULL,
            actual_tonnes REAL NOT NULL,
            scheduled_minutes INTEGER NOT NULL,
            downtime_minutes INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    connection.commit()
    return connection


def validate_shift(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("El turno debe ser un objeto JSON.")
    try:
        shift_date = date.fromisoformat(value["shift_date"])
        name = str(value["name"]).strip()
        planned = float(value["planned_tonnes"])
        actual = float(value["actual_tonnes"])
        scheduled = int(value["scheduled_minutes"])
        downtime = int(value["downtime_minutes"])
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        raise ValueError("Revisa fecha, nombre y valores numéricos del turno.") from exc
    if name not in ("Día", "Noche"):
        raise ValueError("El turno debe ser Día o Noche.")
    if planned <= 0 or actual < 0 or not all(map(_finite, (planned, actual))):
        raise ValueError("El plan debe ser positivo y la producción no puede ser negativa.")
    if not 1 <= scheduled <= 1440 or not 0 <= downtime <= scheduled:
        raise ValueError("Los minutos programados deben estar entre 1 y 1440; la detención no puede superarlos.")
    return {
        "shift_date": shift_date.isoformat(), "name": name,
        "planned_tonnes": planned, "actual_tonnes": actual,
        "scheduled_minutes": scheduled, "downtime_minutes": downtime,
    }


def _finite(number: float) -> bool:
    return number != float("inf") and number != float("-inf") and number == number


def with_kpis(row: sqlite3.Row | dict) -> dict:
    item = dict(row)
    operating = item["scheduled_minutes"] - item["downtime_minutes"]
    item["compliance_pct"] = round(100 * item["actual_tonnes"] / item["planned_tonnes"], 1)
    item["availability_pct"] = round(100 * operating / item["scheduled_minutes"], 1)
    item["tonnes_per_operating_hour"] = round(item["actual_tonnes"] * 60 / operating, 1) if operating else None
    return item


def list_shifts() -> list[dict]:
    with closing(connect()) as db:
        rows = db.execute("SELECT * FROM shifts ORDER BY shift_date DESC, id DESC").fetchall()
    return [with_kpis(row) for row in rows]


def create_shift(payload: object) -> dict:
    shift = validate_shift(payload)
    with closing(connect()) as db, db:
        cursor = db.execute("""
            INSERT INTO shifts (shift_date, name, planned_tonnes, actual_tonnes,
                                scheduled_minutes, downtime_minutes)
            VALUES (:shift_date, :name, :planned_tonnes, :actual_tonnes,
                    :scheduled_minutes, :downtime_minutes)
        """, shift)
        row = db.execute("SELECT * FROM shifts WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return with_kpis(row)


class Handler(BaseHTTPRequestHandler):
    def _json(self, status: int, body: object) -> None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/health":
            self._json(200, {"status": "ok"})
        elif path == "/api/shifts":
            self._json(200, {"shifts": list_shifts()})
        elif path in ("/", "/index.html", "/styles.css", "/app.js"):
            filename = "index.html" if path == "/" else path.lstrip("/")
            mime = {"index.html": "text/html", "styles.css": "text/css", "app.js": "text/javascript"}[filename]
            data = (ROOT / "static" / filename).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", f"{mime}; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self._json(404, {"error": "Ruta no encontrada."})

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/shifts":
            return self._json(404, {"error": "Ruta no encontrada."})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 1 <= length <= 16384:
                raise ValueError("El cuerpo debe contener un JSON de hasta 16 KB.")
            payload = json.loads(self.rfile.read(length))
            created = create_shift(payload)
        except (ValueError, json.JSONDecodeError) as exc:
            return self._json(400, {"error": str(exc)})
        self._json(HTTPStatus.CREATED, created)

    def do_DELETE(self) -> None:
        path = urlparse(self.path).path
        if not path.startswith("/api/shifts/"):
            return self._json(404, {"error": "Ruta no encontrada."})
        try:
            shift_id = int(path.rsplit("/", 1)[1])
        except ValueError:
            return self._json(400, {"error": "ID inválido."})
        with closing(connect()) as db, db:
            deleted = db.execute("DELETE FROM shifts WHERE id = ?", (shift_id,)).rowcount
        self._json(200 if deleted else 404, {"deleted": bool(deleted)})


def main() -> None:
    connect().close()
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Titan Shift en http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
