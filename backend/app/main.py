from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

from app.routers import (
    compatibility,
    parts,
    recommendations,
)


app = FastAPI(
    title="PC Auto Builder API",
    description="컴퓨터 부품 추천 및 호환성 검사 API",
    version="0.4.0",
)


app.include_router(parts.router)
app.include_router(compatibility.router)
app.include_router(recommendations.router)


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


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "message": "PC Auto Builder 서버가 실행 중입니다.",
        "manual_builder": "/app",
        "auto_recommendation": "/recommend",
        "admin": "/admin",
        "api_docs": "/docs",
    }


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
