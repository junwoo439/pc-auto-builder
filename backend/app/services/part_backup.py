from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.data.database import (
    DATABASE_PATH,
    connect_database,
    extract_source_url,
    initialize_database,
)


_DEFAULT_SEED_FILE = Path(__file__).resolve().parents[1] / "data" / "exported_parts.json"
SEED_FILE = Path(
    os.getenv("PC_PARTS_SEED_PATH", str(_DEFAULT_SEED_FILE))
).expanduser().resolve()
BACKUP_DIR = Path(
    os.getenv("PC_PARTS_BACKUP_DIR", str(DATABASE_PATH.parent / "backups"))
).expanduser().resolve()

LEGACY_SAMPLE_MODELS = {
    "Ryzen 5 7600",
    "PRO B650M-A WIFI",
    "PRIME B450M-A",
    "GeForce RTX 4060 VENTUS 2X",
    "DDR5 16GB 5600MHz",
    "DDR4 16GB 3200MHz",
    "Standard M-ATX Case",
    "Compact Mini-ITX Case",
    "600W 80PLUS Bronze",
    "450W Standard PSU",
    "Compact M-ATX Case",
}


def ensure_parts_table() -> None:
    initialize_database()


def parse_specifications(raw_value: object) -> dict[str, object]:
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


def normalize_part(raw_part: dict[str, object]) -> dict[str, object]:
    category = str(raw_part.get("category", "")).strip().lower()
    manufacturer = str(raw_part.get("manufacturer", "")).strip()
    model_name = str(raw_part.get("model_name", "")).strip()

    if not category:
        raise ValueError("부품 종류가 없습니다.")
    if not manufacturer:
        raise ValueError("제조사가 없습니다.")
    if not model_name:
        raise ValueError("제품명이 없습니다.")

    try:
        price = int(raw_part.get("price", 0))
    except (TypeError, ValueError) as error:
        raise ValueError("가격이 올바른 숫자가 아닙니다.") from error

    if price < 0:
        raise ValueError("가격은 0 이상이어야 합니다.")

    specifications = parse_specifications(raw_part.get("specifications", {}))

    return {
        "category": category,
        "manufacturer": manufacturer,
        "model_name": model_name,
        "price": price,
        "specifications": specifications,
        "source_url": extract_source_url(specifications),
    }


def export_parts_payload() -> dict[str, object]:
    ensure_parts_table()

    with connect_database() as connection:
        rows = connection.execute(
            """
            SELECT id, category, manufacturer, model_name, price,
                   specifications, source_url
            FROM parts
            ORDER BY id
            """
        ).fetchall()

    parts: list[dict[str, object]] = []
    for row in rows:
        specs = parse_specifications(row["specifications"])
        if row["source_url"] and not specs.get("source_url"):
            specs["source_url"] = row["source_url"]

        parts.append(
            {
                "id": int(row["id"]),
                "category": str(row["category"]),
                "manufacturer": str(row["manufacturer"]),
                "model_name": str(row["model_name"]),
                "price": int(row["price"]),
                "specifications": specs,
            }
        )

    return {
        "format": "pc-auto-builder-parts",
        "version": 2,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "count": len(parts),
        "parts": parts,
    }


def save_seed_file() -> Path:
    payload = export_parts_payload()
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)

    SEED_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEED_FILE.write_text(serialized, encoding="utf-8")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    runtime_backup = BACKUP_DIR / f"exported_parts-{timestamp}.json"
    runtime_backup.write_text(serialized, encoding="utf-8")

    return SEED_FILE


def extract_parts_from_payload(payload: object) -> list[dict[str, object]]:
    if isinstance(payload, list):
        raw_parts = payload
    elif isinstance(payload, dict):
        raw_parts = payload.get("parts", [])
    else:
        raise ValueError("지원하지 않는 백업 형식입니다.")

    if not isinstance(raw_parts, list):
        raise ValueError("parts 항목은 배열이어야 합니다.")

    return [item for item in raw_parts if isinstance(item, dict)]


def find_existing_part_id(
    connection: Any,
    part: dict[str, object],
) -> int | None:
    source_url = part.get("source_url")

    if source_url:
        row = connection.execute(
            "SELECT id FROM parts WHERE source_url = ? LIMIT 1",
            (source_url,),
        ).fetchone()
        if row is not None:
            return int(row["id"])

    row = connection.execute(
        """
        SELECT id
        FROM parts
        WHERE LOWER(category) = LOWER(?)
          AND LOWER(manufacturer) = LOWER(?)
          AND LOWER(model_name) = LOWER(?)
        LIMIT 1
        """,
        (
            part["category"],
            part["manufacturer"],
            part["model_name"],
        ),
    ).fetchone()

    return int(row["id"]) if row is not None else None


def import_parts_payload(
    payload: object,
    replace_existing: bool = False,
) -> dict[str, object]:
    ensure_parts_table()
    raw_parts = extract_parts_from_payload(payload)

    created = 0
    updated = 0
    failed = 0
    errors: list[dict[str, object]] = []

    with connect_database() as connection:
        if replace_existing:
            connection.execute("DELETE FROM parts")

        for index, raw_part in enumerate(raw_parts, start=1):
            try:
                part = normalize_part(raw_part)
                existing_id = find_existing_part_id(connection, part)
                specifications_json = json.dumps(
                    part["specifications"], ensure_ascii=False
                )

                if existing_id is None:
                    connection.execute(
                        """
                        INSERT INTO parts (
                            category, manufacturer, model_name, price,
                            specifications, source_url
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            part["category"],
                            part["manufacturer"],
                            part["model_name"],
                            part["price"],
                            specifications_json,
                            part["source_url"],
                        ),
                    )
                    created += 1
                else:
                    connection.execute(
                        """
                        UPDATE parts
                        SET category = ?, manufacturer = ?, model_name = ?,
                            price = ?, specifications = ?, source_url = ?
                        WHERE id = ?
                        """,
                        (
                            part["category"],
                            part["manufacturer"],
                            part["model_name"],
                            part["price"],
                            specifications_json,
                            part["source_url"],
                            existing_id,
                        ),
                    )
                    updated += 1

            except Exception as error:
                failed += 1
                errors.append(
                    {
                        "index": index,
                        "model_name": raw_part.get("model_name", "알 수 없음"),
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


def _database_state() -> tuple[int, set[str]]:
    with connect_database() as connection:
        rows = connection.execute("SELECT model_name FROM parts ORDER BY id").fetchall()

    return len(rows), {str(row["model_name"]) for row in rows}


def restore_seed_if_database_empty() -> dict[str, object]:
    ensure_parts_table()
    current_count, current_models = _database_state()
    legacy_sample = (
        current_count == len(LEGACY_SAMPLE_MODELS)
        and current_models == LEGACY_SAMPLE_MODELS
    )

    if current_count > 0 and not legacy_sample:
        return {
            "status": "skipped",
            "message": "DB에 기존 부품이 있어 자동 복원을 생략했습니다.",
            "count": current_count,
        }

    if not SEED_FILE.exists():
        return {
            "status": "no_seed",
            "message": "코드용 시드 파일이 없습니다.",
            "count": current_count,
        }

    try:
        payload = json.loads(SEED_FILE.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        return {"status": "failed", "message": str(error), "count": current_count}

    result = import_parts_payload(
        payload=payload,
        replace_existing=legacy_sample,
    )

    return {
        "status": "restored_legacy_sample" if legacy_sample else "restored",
        "message": (
            "기존 예제 11개를 제거하고 시드 데이터로 복원했습니다."
            if legacy_sample
            else "코드용 시드 파일에서 부품을 자동 복원했습니다."
        ),
        **result,
    }


def get_backup_status() -> dict[str, object]:
    payload = export_parts_payload()
    return {
        "database_count": payload["count"],
        "database_file": str(DATABASE_PATH),
        "seed_exists": SEED_FILE.exists(),
        "seed_file": str(SEED_FILE),
        "backup_directory": str(BACKUP_DIR),
        "deployment_note": (
            "Railway/Docker에서는 PC_PARTS_DB_PATH와 PC_PARTS_BACKUP_DIR을 "
            "영구 볼륨 경로로 설정해야 재배포 후에도 데이터가 유지됩니다."
        ),
    }
