from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.routers.parts import verify_admin_key
from app.services.bulk_importer import import_bulk_products
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
        default=10,
        ge=1,
        le=50,
    )

    max_products: int = Field(
        default=100,
        ge=1,
        le=300,
    )


@router.post(
    "/web",
    dependencies=[Depends(verify_admin_key)],
)
def import_web_products(
    request: WebImportRequest,
) -> dict[str, object]:
    return import_from_urls(
        seed_urls=request.urls,
        category=request.category,
        discover_links=request.discover_links,
        max_products=request.max_products,
    )


@router.post(
    "/bulk",
    dependencies=[Depends(verify_admin_key)],
)
def bulk_import_web_products(
    request: BulkWebImportRequest,
) -> dict[str, object]:
    return import_bulk_products(
        seed_urls=request.urls,
        category=request.category,
        max_pages=request.max_pages,
        max_products=request.max_products,
    )
