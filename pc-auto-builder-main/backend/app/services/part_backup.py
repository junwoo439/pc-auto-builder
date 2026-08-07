import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.data.database import connect_database


SEED_FILE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "exported_parts.json"
)


def ensure_parts_table() -> None:
    with connect_database() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                manufacturer TEXT NOT NULL,
                model_name TEXT NOT NULL,
                price INTEGER NOT NULL,
                specifications TEXT NOT NULL
            )
            """
        )

        connection.commit()


def parse_specifications(
    raw_value: object,
) -> dict[str, object]:
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


def normalize_part(
    raw_part: dict[str, object],
) -> dict[str, object]:
    category = str(
        raw_part.get("category", "")
    ).strip().lower()

    manufacturer = str(
        raw_part.get("manufacturer", "")
    ).strip()

    model_name = str(
        raw_part.get("model_name", "")
    ).strip()

    if not category:
        raise ValueError("부품 종류가 없습니다.")

    if not manufacturer:
        raise ValueError("제조사가 없습니다.")

    if not model_name:
        raise ValueError("제품명이 없습니다.")

    try:
        price = int(raw_part.get("price", 0))
    except (TypeError, ValueError) as error:
        raise ValueError(
            "가격이 올바른 숫자가 아닙니다."
        ) from error

    if price < 0:
        raise ValueError(
            "가격은 0 이상이어야 합니다."
        )

    specifications = parse_specifications(
        raw_part.get("specifications", {})
    )

    return {
        "category": category,
        "manufacturer": manufacturer,
        "model_name": model_name,
        "price": price,
        "specifications": specifications,
    }


def export_parts_payload() -> dict[str, object]:
    ensure_parts_table()

    with connect_database() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                category,
                manufacturer,
                model_name,
                price,
                specifications
            FROM parts
            ORDER BY id
            """
        ).fetchall()

    parts: list[dict[str, object]] = []

    for row in rows:
        parts.append(
            {
                "id": int(row["id"]),
                "category": str(row["category"]),
                "manufacturer": str(
                    row["manufacturer"]
                ),
                "model_name": str(
                    row["model_name"]
                ),
                "price": int(row["price"]),
                "specifications":
                    parse_specifications(
                        row["specifications"]
                    ),
            }
        )

    return {
        "format": "pc-auto-builder-parts",
        "version": 1,
        "exported_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "count": len(parts),
        "parts": parts,
    }


def save_seed_file() -> Path:
    payload = export_parts_payload()

    SEED_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    SEED_FILE.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return SEED_FILE


def extract_parts_from_payload(
    payload: object,
) -> list[dict[str, object]]:
    if isinstance(payload, list):
        raw_parts = payload

    elif isinstance(payload, dict):
        raw_parts = payload.get("parts", [])

    else:
        raise ValueError(
            "지원하지 않는 백업 형식입니다."
        )

    if not isinstance(raw_parts, list):
        raise ValueError(
            "parts 항목은 배열이어야 합니다."
        )

    result: list[dict[str, object]] = []

    for item in raw_parts:
        if not isinstance(item, dict):
            continue

        result.append(item)

    return result


def find_existing_part_id(
    connection: Any,
    part: dict[str, object],
) -> int | None:
    specifications = part["specifications"]

    source_url = None

    if isinstance(specifications, dict):
        source_value = specifications.get(
            "source_url"
        )

        if source_value:
            source_url = str(source_value)

    if source_url:
        rows = connection.execute(
            """
            SELECT
                id,
                specifications
            FROM parts
            """
        ).fetchall()

        for row in rows:
            stored_specs = parse_specifications(
                row["specifications"]
            )

            if (
                stored_specs.get("source_url")
                == source_url
            ):
                return int(row["id"])

    row = connection.execute(
        """
        SELECT id
        FROM parts
        WHERE
            LOWER(manufacturer) = LOWER(?)
            AND LOWER(model_name) = LOWER(?)
        LIMIT 1
        """,
        (
            part["manufacturer"],
            part["model_name"],
        ),
    ).fetchone()

    if row is None:
        return None

    return int(row["id"])


def import_parts_payload(
    payload: object,
    replace_existing: bool = False,
) -> dict[str, object]:
    ensure_parts_table()

    raw_parts = extract_parts_from_payload(
        payload
    )

    created = 0
    updated = 0
    failed = 0
    errors: list[dict[str, object]] = []

    with connect_database() as connection:
        if replace_existing:
            connection.execute(
                "DELETE FROM parts"
            )

        for index, raw_part in enumerate(
            raw_parts,
            start=1,
        ):
            try:
                part = normalize_part(raw_part)

                existing_id = find_existing_part_id(
                    connection,
                    part,
                )

                specifications_json = json.dumps(
                    part["specifications"],
                    ensure_ascii=False,
                )

                if existing_id is None:
                    connection.execute(
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
                            specifications_json,
                        ),
                    )

                    created += 1

                else:
                    connection.execute(
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
                            specifications_json,
                            existing_id,
                        ),
                    )

                    updated += 1

            except Exception as error:
                failed += 1

                errors.append(
                    {
                        "index": index,
                        "model_name":
                            raw_part.get(
                                "model_name",
                                "알 수 없음",
                            ),
                        "message": str(error),
                    }
                )

        connection.commit()

    return {
        "total": len(raw_parts),
        "created": created,
        "updated": updated,
        "failed": failed,
        "replace_existing": replace_existing,
        "errors": errors,
    }


def restore_seed_if_database_empty(
) -> dict[str, object]:
    ensure_parts_table()

    with connect_database() as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS count FROM parts"
        ).fetchone()

        current_count = int(row["count"])

    if current_count > 0:
        return {
            "status": "skipped",
            "message": (
                "DB에 기존 부품이 있어 "
                "자동 복원을 생략했습니다."
            ),
            "count": current_count,
        }

    if not SEED_FILE.exists():
        return {
            "status": "no_seed",
            "message": (
                "코드용 시드 파일이 없습니다."
            ),
            "count": 0,
        }

    try:
        payload = json.loads(
            SEED_FILE.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ) as error:
        return {
            "status": "failed",
            "message": str(error),
            "count": 0,
        }

    result = import_parts_payload(
        payload=payload,
        replace_existing=False,
    )

    return {
        "status": "restored",
        "message": (
            "코드용 시드 파일에서 "
            "부품을 자동 복원했습니다."
        ),
        **result,
    }


def get_backup_status() -> dict[str, object]:
    payload = export_parts_payload()

    return {
        "database_count": payload["count"],
        "seed_exists": SEED_FILE.exists(),
        "seed_file": str(SEED_FILE),
    }
