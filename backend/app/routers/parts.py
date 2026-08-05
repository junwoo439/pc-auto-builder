import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Query,
)
from pydantic import BaseModel, Field

from app.data.parts import find_part_by_id
from app.data.repository import (
    create_part,
    delete_part,
    list_parts,
    update_part,
)


ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ENV_FILE, override=True)


router = APIRouter(
    prefix="/parts",
    tags=["parts"],
)


class PartInput(BaseModel):
    category: str = Field(min_length=1)
    manufacturer: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    price: int = Field(ge=0)
    specifications: dict[str, object]


def verify_admin_key(
    x_admin_key: str | None = Header(default=None),
) -> None:
    correct_key = os.getenv("ADMIN_API_KEY")

    if not correct_key:
        raise HTTPException(
            status_code=500,
            detail="서버에 관리자 키가 설정되지 않았습니다.",
        )

    if x_admin_key is None:
        raise HTTPException(
            status_code=401,
            detail="관리자 키가 필요합니다.",
        )

    if not secrets.compare_digest(
        x_admin_key,
        correct_key,
    ):
        raise HTTPException(
            status_code=401,
            detail="관리자 키가 올바르지 않습니다.",
        )


@router.get("/")
def get_parts(
    category: str | None = Query(default=None),
) -> list[dict[str, object]]:
    normalized_category = None

    if category is not None:
        normalized_category = category.strip().lower()

    return list_parts(normalized_category)


@router.get("/{part_id}")
def get_part(part_id: int) -> dict[str, object]:
    part = find_part_by_id(part_id)

    if part is None:
        raise HTTPException(
            status_code=404,
            detail="해당 부품을 찾을 수 없습니다.",
        )

    return part


@router.post(
    "/",
    status_code=201,
    dependencies=[Depends(verify_admin_key)],
)
def add_part(
    request: PartInput,
) -> dict[str, object]:
    data = request.model_dump()

    data["category"] = request.category.strip().lower()
    data["manufacturer"] = request.manufacturer.strip()
    data["model_name"] = request.model_name.strip()

    return create_part(data)


@router.put(
    "/{part_id}",
    dependencies=[Depends(verify_admin_key)],
)
def edit_part(
    part_id: int,
    request: PartInput,
) -> dict[str, object]:
    data = request.model_dump()

    data["category"] = request.category.strip().lower()
    data["manufacturer"] = request.manufacturer.strip()
    data["model_name"] = request.model_name.strip()

    updated_part = update_part(
        part_id,
        data,
    )

    if updated_part is None:
        raise HTTPException(
            status_code=404,
            detail="수정할 부품을 찾을 수 없습니다.",
        )

    return updated_part


@router.delete(
    "/{part_id}",
    dependencies=[Depends(verify_admin_key)],
)
def remove_part(part_id: int) -> dict[str, str]:
    deleted = delete_part(part_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="삭제할 부품을 찾을 수 없습니다.",
        )

    return {
        "message": "부품이 삭제되었습니다.",
    }
