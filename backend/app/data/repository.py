import json

from app.data.database import (
    connect_database,
    convert_row,
    initialize_database,
)


initialize_database()


def list_parts(
    category: str | None = None,
) -> list[dict[str, object]]:
    with connect_database() as connection:
        if category is None:
            rows = connection.execute(
                "SELECT * FROM parts ORDER BY id"
            ).fetchall()
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


def create_part(
    part: dict[str, object],
) -> dict[str, object]:
    with connect_database() as connection:
        cursor = connection.execute(
            """
            INSERT INTO parts (
                category,
                manufacturer,
                model_name,
                price,
                specifications
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                part["category"],
                part["manufacturer"],
                part["model_name"],
                part["price"],
                json.dumps(
                    part["specifications"],
                    ensure_ascii=False,
                ),
            ),
        )

        connection.commit()

        part_id = int(cursor.lastrowid)

        row = connection.execute(
            "SELECT * FROM parts WHERE id = ?",
            (part_id,),
        ).fetchone()

    if row is None:
        raise RuntimeError("생성된 부품을 찾을 수 없습니다.")

    return convert_row(row)


def update_part(
    part_id: int,
    part: dict[str, object],
) -> dict[str, object] | None:
    with connect_database() as connection:
        cursor = connection.execute(
            """
            UPDATE parts
            SET
                category = ?,
                manufacturer = ?,
                model_name = ?,
                price = ?,
                specifications = ?
            WHERE id = ?
            """,
            (
                part["category"],
                part["manufacturer"],
                part["model_name"],
                part["price"],
                json.dumps(
                    part["specifications"],
                    ensure_ascii=False,
                ),
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

    if row is None:
        return None

    return convert_row(row)


def delete_part(part_id: int) -> bool:
    with connect_database() as connection:
        cursor = connection.execute(
            "DELETE FROM parts WHERE id = ?",
            (part_id,),
        )

        connection.commit()

    return cursor.rowcount > 0
