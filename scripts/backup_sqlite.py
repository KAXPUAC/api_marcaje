#!/usr/bin/env python3
"""Crea un respaldo consistente de la base SQLite de la API."""

from __future__ import annotations

import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


def backup_database(source: Path, destination_directory: Path, retention: int) -> Path:
    if not source.is_file():
        raise FileNotFoundError(f"No existe la base SQLite: {source}")
    if retention < 1:
        raise ValueError("La retención debe ser mayor que cero")

    destination_directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = destination_directory / f"api_marcaje-{timestamp}.sqlite3"
    temporary = destination.with_suffix(".sqlite3.tmp")

    try:
        with sqlite3.connect(source) as source_connection:
            with sqlite3.connect(temporary) as destination_connection:
                source_connection.backup(destination_connection)
                result = destination_connection.execute(
                    "PRAGMA integrity_check"
                ).fetchone()
                if not result or result[0] != "ok":
                    raise RuntimeError("El respaldo SQLite no pasó integrity_check")
                destination_connection.commit()

        os.chmod(temporary, 0o600)
        temporary.replace(destination)
        _remove_old_backups(destination_directory, retention)
        return destination
    finally:
        temporary.unlink(missing_ok=True)


def _remove_old_backups(directory: Path, retention: int) -> None:
    backups = sorted(
        directory.glob("api_marcaje-*.sqlite3"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for old_backup in backups[retention:]:
        old_backup.unlink()


def main() -> int:
    source = Path(os.getenv("SQLITE_DB_PATH", "data/api_marcaje.sqlite3"))
    destination_directory = Path(
        os.getenv("SQLITE_BACKUP_DIR", "backups")
    )
    retention = int(os.getenv("SQLITE_BACKUP_RETENTION", "7"))
    backup = backup_database(source, destination_directory, retention)
    print(f"Respaldo creado: {backup}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        print(f"Error creando respaldo SQLite: {error}", file=sys.stderr)
        raise SystemExit(1) from error
