from __future__ import annotations

import os
import secrets
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from app.data.parts import find_part_by_id
from app.data.repository import (
    DuplicatePartError,
    create_part,
    delete_part,
    list_parts,
    update_part,
)


ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ENV_FILE, override=False)

router = APIRouter(prefix="/parts", tags=["parts"])


class PartInput(BaseModel):
    category: str = Field(min_length=1, max_length=50)
    manufacturer: str = Field(min_length=1, max_length=200)
    model_name: str = Field(min_length=1, max_length=500)
    price: int = Field(ge=0, le=2_000_000_000)
    specifications: dict[str, object] = Field(default_factory=dict)

    @field_validator("category", "manufacturer", "model_name")
    @classmethod
    def strip_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("빈 문자열은 사용할 수 없습니다.")
        return normalized


def verify_admin_key(x_admin_key: str | None = Header(default=None)) -> None:
    correct_key = os.getenv("ADMIN_API_KEY")

    if not correct_key:
        raise HTTPException(
            status_code=500,
            detail="서버에 ADMIN_API_KEY가 설정되지 않았습니다.",
        )

    if x_admin_key is None:
        raise HTTPException(status_code=401, detail="관리자 키가 필요합니다.")

    if not secrets.compare_digest(x_admin_key, correct_key):
        raise HTTPException(status_code=401, detail="관리자 키가 올바르지 않습니다.")


def normalize_part_input(request: PartInput) -> dict[str, object]:
    data = request.model_dump()
    data["category"] = request.category.lower()
    return data


@router.get("/")
def get_parts(
    category: str | None = Query(default=None, max_length=50),
) -> list[dict[str, object]]:
    normalized_category = category.strip().lower() if category else None
    return list_parts(normalized_category)


@router.get("/{part_id}")
def get_part(part_id: int) -> dict[str, object]:
    part = find_part_by_id(part_id)
    if part is None:
        raise HTTPException(status_code=404, detail="해당 부품을 찾을 수 없습니다.")
    return part


@router.post("/", status_code=201, dependencies=[Depends(verify_admin_key)])
def add_part(request: PartInput) -> dict[str, object]:
    try:
        return create_part(normalize_part_input(request))
    except DuplicatePartError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.put("/{part_id}", dependencies=[Depends(verify_admin_key)])
def edit_part(part_id: int, request: PartInput) -> dict[str, object]:
    try:
        updated_part = update_part(part_id, normalize_part_input(request))
    except DuplicatePartError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    if updated_part is None:
        raise HTTPException(status_code=404, detail="수정할 부품을 찾을 수 없습니다.")

    return updated_part


@router.delete("/{part_id}", dependencies=[Depends(verify_admin_key)])
def remove_part(part_id: int) -> dict[str, str]:
    if not delete_part(part_id):
        raise HTTPException(status_code=404, detail="삭제할 부품을 찾을 수 없습니다.")

    return {"message": "부품이 삭제되었습니다."}
