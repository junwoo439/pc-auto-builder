from __future__ import annotations

import json
import sqlite3

from app.data.database import (
    connect_database,
    convert_row,
    extract_source_url,
    initialize_database,
)


class DuplicatePartError(ValueError):
    pass


def _serialize_part(part: dict[str, object]) -> tuple[str, str | None]:
    specifications = part.get("specifications", {})
    if not isinstance(specifications, dict):
        raise ValueError("specifications는 객체여야 합니다.")

    source_url = extract_source_url(specifications)
    return json.dumps(specifications, ensure_ascii=False), source_url


def list_parts(category: str | None = None) -> list[dict[str, object]]:
    initialize_database()

    with connect_database() as connection:
        if category is None:
            rows = connection.execute("SELECT * FROM parts ORDER BY id").fetchall()
        else:
            rows = connection.execute(
                """
                SELECT *
                FROM parts
                WHERE LOWER(category) = LOWER(?)
                ORDER BY id
                """,
                (category,),
            ).fetchall()

    return [convert_row(row) for row in rows]


def create_part(part: dict[str, object]) -> dict[str, object]:
    initialize_database()
    specifications_json, source_url = _serialize_part(part)

    try:
        with connect_database() as connection:
            cursor = connection.execute(
                """
                INSERT INTO parts (
                    category,
                    manufacturer,
                    model_name,
                    price,
                    specifications,
                    source_url
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    part["category"],
                    part["manufacturer"],
                    part["model_name"],
                    part["price"],
                    specifications_json,
                    source_url,
                ),
            )
            connection.commit()
            part_id = int(cursor.lastrowid)
            row = connection.execute(
                "SELECT * FROM parts WHERE id = ?",
                (part_id,),
            ).fetchone()
    except sqlite3.IntegrityError as error:
        raise DuplicatePartError(
            "같은 출처 URL 또는 같은 제조사·모델명의 부품이 이미 있습니다."
        ) from error

    if row is None:
        raise RuntimeError("생성된 부품을 찾을 수 없습니다.")

    return convert_row(row)


def update_part(
    part_id: int,
    part: dict[str, object],
) -> dict[str, object] | None:
    initialize_database()
    specifications_json, source_url = _serialize_part(part)

    try:
        with connect_database() as connection:
            cursor = connection.execute(
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
                    part["category"],
                    part["manufacturer"],
                    part["model_name"],
                    part["price"],
                    specifications_json,
                    source_url,
                    part_id,
                ),
            )

            if cursor.rowcount == 0:
                return None

            connection.commit()
            row = connection.execute(
                "SELECT * FROM parts WHERE id = ?",
                (part_id,),
            ).fetchone()
    except sqlite3.IntegrityError as error:
        raise DuplicatePartError(
            "같은 출처 URL 또는 같은 제조사·모델명의 부품이 이미 있습니다."
        ) from error

    return convert_row(row) if row is not None else None


def delete_part(part_id: int) -> bool:
    initialize_database()

    with connect_database() as connection:
        cursor = connection.execute(
            "DELETE FROM parts WHERE id = ?",
            (part_id,),
        )
        connection.commit()

    return cursor.rowcount > 0
