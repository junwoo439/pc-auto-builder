import json
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.data.database import connect_database
from app.routers.parts import verify_admin_key


router = APIRouter(
    prefix="/parts-bulk",
    tags=["parts-bulk"],
)


class PartSelectionRequest(BaseModel):
    part_ids: list[int] = Field(
        min_length=1,
        max_length=5000,
    )


def normalize_ids(
    part_ids: list[int],
) -> list[int]:
    return sorted(
        {
            int(part_id)
            for part_id in part_ids
            if int(part_id) > 0
        }
    )


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


def get_parts_for_export(
    part_ids: list[int] | None = None,
) -> list[dict[str, object]]:
    with connect_database() as connection:
        if part_ids is None:
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

        else:
            normalized_ids = normalize_ids(part_ids)

            if not normalized_ids:
                return []

            placeholders = ",".join(
                "?"
                for _ in normalized_ids
            )

            rows = connection.execute(
                f"""
                SELECT
                    id,
                    category,
                    manufacturer,
                    model_name,
                    price,
                    specifications
                FROM parts
                WHERE id IN ({placeholders})
                ORDER BY id
                """,
                normalized_ids,
            ).fetchall()

    return [
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
        for row in rows
    ]


def build_export_payload(
    part_ids: list[int] | None = None,
) -> dict[str, object]:
    parts = get_parts_for_export(part_ids)

    return {
        "format": "pc-auto-builder-parts",
        "version": 1,
        "exported_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "count": len(parts),
        "parts": parts,
    }


def make_download_response(
    payload: dict[str, object],
    filename_prefix: str,
) -> JSONResponse:
    timestamp = datetime.now().strftime(
        "%Y%m%d-%H%M%S"
    )

    filename = (
        f"{filename_prefix}-{timestamp}.json"
    )

    return JSONResponse(
        content=payload,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{filename}"'
            )
        },
    )


@router.get(
    "/export-all",
    dependencies=[Depends(verify_admin_key)],
)
def export_all_parts() -> JSONResponse:
    payload = build_export_payload()

    if payload["count"] == 0:
        raise HTTPException(
            status_code=404,
            detail="다운로드할 부품이 없습니다.",
        )

    return make_download_response(
        payload,
        "all-pc-parts",
    )


@router.post(
    "/export-selected",
    dependencies=[Depends(verify_admin_key)],
)
def export_selected_parts(
    request: PartSelectionRequest,
) -> JSONResponse:
    payload = build_export_payload(
        request.part_ids
    )

    if payload["count"] == 0:
        raise HTTPException(
            status_code=404,
            detail="선택한 부품을 찾을 수 없습니다.",
        )

    return make_download_response(
        payload,
        "selected-pc-parts",
    )


@router.post(
    "/delete-selected",
    dependencies=[Depends(verify_admin_key)],
)
def delete_selected_parts(
    request: PartSelectionRequest,
) -> dict[str, object]:
    normalized_ids = normalize_ids(
        request.part_ids
    )

    if not normalized_ids:
        raise HTTPException(
            status_code=400,
            detail="삭제할 부품을 선택하세요.",
        )

    placeholders = ",".join(
        "?"
        for _ in normalized_ids
    )

    with connect_database() as connection:
        cursor = connection.execute(
            f"""
            DELETE FROM parts
            WHERE id IN ({placeholders})
            """,
            normalized_ids,
        )

        connection.commit()

        deleted_count = cursor.rowcount

    return {
        "message": (
            f"{deleted_count}개의 부품을 삭제했습니다."
        ),
        "deleted_count": deleted_count,
    }
