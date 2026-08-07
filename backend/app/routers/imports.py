from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.routers.parts import verify_admin_key
from app.services.bulk_importer import import_bulk_products
from app.services.import_jobs import create_import_job, get_import_job
from app.services.product_importer import import_from_urls


router = APIRouter(
    prefix="/imports",
    tags=["imports"],
)


PartCategory = Literal[
    "cpu",
    "motherboard",
    "ram",
    "gpu",
    "case",
    "psu",
    "cooler",
    "storage",
]


class WebImportRequest(BaseModel):
    category: PartCategory

    urls: list[str] = Field(
        min_length=1,
        max_length=10,
    )

    discover_links: bool = True

    max_products: int = Field(
        default=20,
        ge=1,
        le=20,
    )


class BulkWebImportRequest(BaseModel):
    category: PartCategory

    urls: list[str] = Field(
        min_length=1,
        max_length=10,
    )

    max_pages: int = Field(
        default=20,
        ge=1,
        le=100,
    )

    max_products: int = Field(
        default=500,
        ge=1,
        le=1000,
    )


@router.post(
    "/web",
    dependencies=[Depends(verify_admin_key)],
)
def import_web_products(
    request: WebImportRequest,
) -> dict[str, object]:
    # 일반 수집은 기존 API 호환성을 위해 동기 처리합니다.
    return import_from_urls(
        seed_urls=request.urls,
        category=request.category,
        discover_links=request.discover_links,
        max_products=request.max_products,
    )


@router.post(
    "/bulk",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_admin_key)],
)
def start_bulk_import(
    request: BulkWebImportRequest,
) -> dict[str, object]:
    return create_import_job(
        "bulk_web_import",
        import_bulk_products,
        seed_urls=list(request.urls),
        category=request.category,
        max_pages=request.max_pages,
        max_products=request.max_products,
    )


@router.get(
    "/jobs/{job_id}",
    dependencies=[Depends(verify_admin_key)],
)
def read_import_job(
    job_id: str,
) -> dict[str, object]:
    job = get_import_job(job_id)

    if job is None:
        raise HTTPException(
            status_code=404,
            detail="수집 작업을 찾을 수 없습니다.",
        )

    return job