from __future__ import annotations

import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any


_DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[2] / "pc_parts.db"
DATABASE_PATH = Path(
    os.getenv("PC_PARTS_DB_PATH", str(_DEFAULT_DATABASE_PATH))
).expanduser().resolve()
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

_SCHEMA_LOCK = threading.Lock()
_SCHEMA_READY = False


def _parse_specifications(raw_value: object) -> dict[str, object]:
    if isinstance(raw_value, dict):
        return raw_value

    if isinstance(raw_value, str):
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError:
            return {}

        if isinstance(parsed, dict):
            return parsed

    return {}


def extract_source_url(specifications: object) -> str | None:
    specs = _parse_specifications(specifications)
    value = specs.get("source_url") or specs.get("spec_source_url")

    if value is None:
        return None

    normalized = str(value).strip()
    return normalized or None


def connect_database() -> sqlite3.Connection:
    connection = sqlite3.connect(
        DATABASE_PATH,
        timeout=30,
        check_same_thread=False,
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 30000")
    connection.execute("PRAGMA synchronous = NORMAL")

    try:
        connection.execute("PRAGMA journal_mode = WAL")
    except sqlite3.DatabaseError:
        # 읽기 전용 파일시스템 등에서 WAL 전환이 불가능해도 기본 모드로 동작합니다.
        pass

    return connection


def _column_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute("PRAGMA table_info(parts)").fetchall()
    return {str(row["name"]) for row in rows}


def _merge_duplicate_rows(
    connection: sqlite3.Connection,
    keep_row: sqlite3.Row,
    duplicate_row: sqlite3.Row,
) -> None:
    keep_specs = _parse_specifications(keep_row["specifications"])
    duplicate_specs = _parse_specifications(duplicate_row["specifications"])
    merged_specs = {**keep_specs, **duplicate_specs}
    source_url = (
        duplicate_row["source_url"]
        or keep_row["source_url"]
        or extract_source_url(merged_specs)
    )

    connection.execute(
        """
        UPDATE parts
        SET category = ?,
            manufacturer = ?,
            model_name = ?,
            price = ?,
            specifications = ?,
            source_url = ?
        WHERE id = ?
        """,
        (
            duplicate_row["category"],
            duplicate_row["manufacturer"],
            duplicate_row["model_name"],
            duplicate_row["price"],
            json.dumps(merged_specs, ensure_ascii=False),
            source_url,
            keep_row["id"],
        ),
    )
    connection.execute(
        "DELETE FROM parts WHERE id = ?",
        (duplicate_row["id"],),
    )


def _deduplicate_parts(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT id, category, manufacturer, model_name, price,
               specifications, source_url
        FROM parts
        ORDER BY id
        """
    ).fetchall()

    source_owner: dict[str, sqlite3.Row] = {}
    name_owner: dict[tuple[str, str, str], sqlite3.Row] = {}
    deleted_ids: set[int] = set()

    for row in rows:
        row_id = int(row["id"])
        if row_id in deleted_ids:
            continue

        source_url = str(row["source_url"] or "").strip()
        name_key = (
            str(row["category"]).strip().casefold(),
            str(row["manufacturer"]).strip().casefold(),
            str(row["model_name"]).strip().casefold(),
        )

        owner = source_owner.get(source_url) if source_url else None
        if owner is None:
            owner = name_owner.get(name_key)

        if owner is None:
            if source_url:
                source_owner[source_url] = row
            name_owner[name_key] = row
            continue

        _merge_duplicate_rows(connection, owner, row)
        deleted_ids.add(row_id)


def initialize_database() -> None:
    global _SCHEMA_READY

    if _SCHEMA_READY:
        return

    with _SCHEMA_LOCK:
        if _SCHEMA_READY:
            return

        with connect_database() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS parts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    manufacturer TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    price INTEGER NOT NULL CHECK(price >= 0),
                    specifications TEXT NOT NULL,
                    source_url TEXT
                )
                """
            )

            columns = _column_names(connection)
            if "source_url" not in columns:
                connection.execute("ALTER TABLE parts ADD COLUMN source_url TEXT")

            rows = connection.execute(
                "SELECT id, specifications, source_url FROM parts"
            ).fetchall()
            for row in rows:
                if row["source_url"]:
                    continue

                source_url = extract_source_url(row["specifications"])
                if source_url:
                    connection.execute(
                        "UPDATE parts SET source_url = ? WHERE id = ?",
                        (source_url, row["id"]),
                    )

            _deduplicate_parts(connection)

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_parts_category
                ON parts(category)
                """
            )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_parts_source_url
                ON parts(source_url)
                WHERE source_url IS NOT NULL AND source_url <> ''
                """
            )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_parts_identity
                ON parts(
                    LOWER(category),
                    LOWER(manufacturer),
                    LOWER(model_name)
                )
                """
            )
            connection.commit()

        _SCHEMA_READY = True


def convert_row(row: sqlite3.Row) -> dict[str, object]:
    specifications = _parse_specifications(row["specifications"])
    row_keys = set(row.keys())
    source_url = row["source_url"] if "source_url" in row_keys else None

    if source_url and not specifications.get("source_url"):
        specifications["source_url"] = source_url

    return {
        "id": int(row["id"]),
        "category": str(row["category"]),
        "manufacturer": str(row["manufacturer"]),
        "model_name": str(row["model_name"]),
        "price": int(row["price"]),
        "specifications": specifications,
    }


def get_all_parts() -> list[dict[str, object]]:
    initialize_database()

    with connect_database() as connection:
        rows = connection.execute("SELECT * FROM parts ORDER BY id").fetchall()

    return [convert_row(row) for row in rows]


def reset_schema_state_for_tests() -> None:
    """테스트에서 DB 경로를 바꾼 뒤 스키마 초기화를 다시 실행할 때 사용합니다."""
    global _SCHEMA_READY
    _SCHEMA_READY = False


def get_part_by_id(part_id: int) -> dict[str, object] | None:
    initialize_database()

    with connect_database() as connection:
        row = connection.execute(
            "SELECT * FROM parts WHERE id = ?",
            (part_id,),
        ).fetchone()

    return convert_row(row) if row is not None else None
