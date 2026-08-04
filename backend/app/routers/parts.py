from fastapi import APIRouter, HTTPException, Query

from app.data.parts import PARTS, find_part_by_id


router = APIRouter(
    prefix="/parts",
    tags=["parts"],
)


@router.get("/")
def get_parts(
    category: str | None = Query(
        default=None,
        description="조회할 부품 종류",
    ),
) -> list[dict[str, object]]:
    if category is None:
        return PARTS

    normalized_category = category.strip().lower()

    return [
        part
        for part in PARTS
        if str(part["category"]).lower() == normalized_category
    ]


@router.get("/{part_id}")
def get_part(part_id: int) -> dict[str, object]:
    part = find_part_by_id(part_id)

    if part is None:
        raise HTTPException(
            status_code=404,
            detail="해당 부품을 찾을 수 없습니다.",
        )

    return part