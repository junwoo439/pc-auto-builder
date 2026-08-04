from fastapi import FastAPI

from app.routers import compatibility, parts


app = FastAPI(
    title="PC Auto Builder API",
    description="컴퓨터 부품 추천 및 호환성 검사 API",
    version="0.1.0",
)


app.include_router(parts.router)
app.include_router(compatibility.router)


@app.get("/")
def read_root() -> dict[str, str]:
    return {
        "message": "PC Auto Builder 서버가 정상적으로 실행 중입니다."
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok"
    }