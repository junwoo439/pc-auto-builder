from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import (
    FileResponse,
    RedirectResponse,
)

from app.routers import (
    spec_updates,
    bulk_parts,
    backups,
    compatibility,
    imports,
    parts,
    recommendations,
)
from app.services.part_backup import (
    restore_seed_if_database_empty,
)


app = FastAPI(
    title="PC Auto Builder API",
    description="컴퓨터 부품 추천 및 호환성 검사 API",
    version="0.7.0",
)


app.include_router(parts.router)
app.include_router(spec_updates.router)
app.include_router(bulk_parts.router)
app.include_router(compatibility.router)
app.include_router(recommendations.router)
app.include_router(imports.router)
app.include_router(backups.router)


restore_seed_if_database_empty()


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "frontend"


def frontend_response(
    filename: str,
) -> FileResponse:
    file_path = FRONTEND_DIR / filename

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"{filename} 파일을 찾을 수 없습니다.",
        )

    return FileResponse(file_path)


@app.get(
    "/",
    include_in_schema=False,
)
def read_root() -> RedirectResponse:
    return RedirectResponse(url="/app")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
    }


@app.get(
    "/app",
    include_in_schema=False,
)
def serve_builder() -> FileResponse:
    return frontend_response("index.html")


@app.get(
    "/recommend",
    include_in_schema=False,
)
def serve_recommendation() -> FileResponse:
    return frontend_response("recommend.html")


@app.get(
    "/admin",
    include_in_schema=False,
)
def serve_admin() -> FileResponse:
    return frontend_response("admin.html")


@app.get(
    "/import",
    include_in_schema=False,
)
def serve_import_page() -> FileResponse:
    return frontend_response("import.html")


@app.get(
    "/bulk-import",
    include_in_schema=False,
)
def serve_bulk_import_page() -> FileResponse:
    return frontend_response("bulk-import.html")


@app.get(
    "/backup",
    include_in_schema=False,
)
def serve_backup_page() -> FileResponse:
    return frontend_response("backup.html")
