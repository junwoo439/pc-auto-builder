from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.data.database import get_all_parts, initialize_database
from app.routers import (
    backups,
    bulk_parts,
    compatibility,
    imports,
    parts,
    recommendations,
    spec_updates,
    ai_compatibility,
)
from app.services.part_backup import restore_seed_if_database_empty


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    app.state.seed_restore = restore_seed_if_database_empty()
    yield


from app.routers import ai_compatibility

app = FastAPI(
    title="PC Auto Builder API",
    description="컴퓨터 부품 추천 및 기본 규격 호환성 검사 API",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(parts.router)
app.include_router(spec_updates.router)
app.include_router(bulk_parts.router)
app.include_router(compatibility.router)
app.include_router(recommendations.router)
app.include_router(imports.router)
app.include_router(backups.router)
app.include_router(ai_compatibility.router)

def frontend_response(filename: str) -> FileResponse:
    file_path = (FRONTEND_DIR / filename).resolve()

    if FRONTEND_DIR.resolve() not in file_path.parents:
        raise HTTPException(status_code=400, detail="잘못된 파일 경로입니다.")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"{filename} 파일을 찾을 수 없습니다.")

    return FileResponse(file_path)


@app.get("/", include_in_schema=False)
def read_root() -> RedirectResponse:
    return RedirectResponse(url="/app")


@app.get("/health")
def health_check() -> dict[str, object]:
    initialize_database()
    return {
        "status": "ok",
        "part_count": len(get_all_parts()),
        "seed_restore": getattr(app.state, "seed_restore", None),
    }


@app.get("/app", include_in_schema=False)
def serve_builder() -> FileResponse:
    return frontend_response("index.html")


@app.get("/recommend", include_in_schema=False)
def serve_recommendation() -> FileResponse:
    return frontend_response("recommend.html")


@app.get("/admin", include_in_schema=False)
def serve_admin() -> FileResponse:
    return frontend_response("admin.html")


@app.get("/import", include_in_schema=False)
def serve_import_page() -> FileResponse:
    return frontend_response("import.html")


@app.get("/bulk-import", include_in_schema=False)
def serve_bulk_import_page() -> FileResponse:
    return frontend_response("bulk-import.html")


@app.get("/backup", include_in_schema=False)
def serve_backup_page() -> FileResponse:
    return frontend_response("backup.html")


@app.get("/3d_view.html", include_in_schema=False)
def serve_3d_view() -> FileResponse:
    return frontend_response("3d_view.html")


if FRONTEND_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(directory=FRONTEND_DIR),
        name="frontend-static",
    )

# ORANGE_AI_RECOMMEND_PAGE_STATUS_BEGIN
# /recommend 화면에 자동 추천의 Orange AI 실제 사용 여부와 실행률을 표시합니다.
from starlette.responses import Response as _OrangeAIStatusResponse

_ORANGE_AI_RECOMMEND_STATUS_UI = r"""
<style id="orange-ai-recommend-status-style">
#orange-ai-recommend-status {
    box-sizing: border-box;
    position: fixed;
    right: 20px;
    bottom: 20px;
    z-index: 99999;
    width: min(390px, calc(100vw - 32px));
    padding: 16px;
    border: 1px solid rgba(127,127,127,.28);
    border-radius: 16px;
    background: rgba(20, 22, 28, .96);
    color: #f5f7fb;
    box-shadow: 0 14px 40px rgba(0,0,0,.28);
    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    line-height: 1.45;
}
#orange-ai-recommend-status .oai-head {
    display:flex;
    align-items:center;
    justify-content:space-between;
    gap:12px;
    margin-bottom:10px;
}
#orange-ai-recommend-status .oai-title {
    font-size:16px;
    font-weight:800;
}
#orange-ai-recommend-status .oai-badge {
    padding:4px 8px;
    border-radius:999px;
    background:#323744;
    font-size:12px;
    font-weight:700;
    white-space:nowrap;
}
#orange-ai-recommend-status[data-active="true"] .oai-badge {
    background:#153f2d;
}
#orange-ai-recommend-status[data-active="false"] .oai-badge {
    background:#4a2b2b;
}
#orange-ai-recommend-status .oai-sub {
    color:#b9c0cc;
    font-size:12px;
    margin-bottom:12px;
}
#orange-ai-recommend-status .oai-grid {
    display:grid;
    grid-template-columns:1fr auto;
    gap:7px 12px;
    font-size:13px;
}
#orange-ai-recommend-status .oai-grid strong {
    text-align:right;
}
#orange-ai-recommend-status .oai-bar {
    height:8px;
    border-radius:999px;
    background:#353945;
    overflow:hidden;
    margin-top:8px;
}
#orange-ai-recommend-status .oai-bar > span {
    display:block;
    height:100%;
    width:0%;
    background:linear-gradient(90deg,#5b8cff,#7bd3a8);
    transition:width .3s ease;
}
#orange-ai-recommend-status .oai-note {
    margin-top:10px;
    color:#9fa7b5;
    font-size:11px;
}
@media (max-width: 700px) {
    #orange-ai-recommend-status {
        position:static;
        width:auto;
        margin:16px;
    }
}
</style>

<section id="orange-ai-recommend-status" data-active="waiting">
    <div class="oai-head">
        <div class="oai-title">🤖 Orange AI 자동 추천</div>
        <div class="oai-badge" id="oai-status-badge">대기 중</div>
    </div>
    <div class="oai-sub" id="oai-status-sub">
        자동 추천을 실행하면 실제 AI 사용 여부와 실행률이 표시됩니다.
    </div>
    <div class="oai-grid">
        <span>최종 순위에 AI 사용</span><strong id="oai-used">-</strong>
        <span>AI 실행 성공률</span><strong id="oai-success-rate">-</strong>
        <span>전체 후보 AI 적용률</span><strong id="oai-coverage-rate">-</strong>
        <span>AI 실행 횟수</span><strong id="oai-counts">-</strong>
        <span>선택 조합 AI 호환 확률</span><strong id="oai-probability">-</strong>
        <span>AI 최종 판정</span><strong id="oai-prediction">-</strong>
    </div>
    <div class="oai-bar" title="AI 실행 성공률">
        <span id="oai-success-bar"></span>
    </div>
    <div class="oai-note">
        실행 성공률 = 정상 AI 추론 수 ÷ AI 추론 시도 수 × 100
    </div>
</section>

<script id="orange-ai-recommend-status-script">
(() => {
    const card = document.getElementById("orange-ai-recommend-status");
    if (!card) return;

    const el = (id) => document.getElementById(id);
    const fmt = (v) => (
        typeof v === "number" && Number.isFinite(v)
            ? `${v.toFixed(1)}%`
            : "-"
    );

    function renderAI(data) {
        const ai = data && data.ai;

        if (!ai) {
            card.dataset.active = "false";
            el("oai-status-badge").textContent = "AI 정보 없음";
            el("oai-status-sub").textContent =
                "자동 추천 응답에 ai 정보가 없습니다. recommendations.py의 Orange AI 패치를 확인하세요.";
            return;
        }

        const used = ai.used_in_ranking === true;
        const success = Number(ai.execution_success_rate_percent ?? 0);
        const coverage = Number(ai.coverage_rate_percent ?? 0);
        const attempted = Number(ai.attempted_candidates ?? 0);
        const successful = Number(ai.successful_candidates ?? 0);
        const failed = Number(ai.failed_candidates ?? 0);

        card.dataset.active = String(used);
        el("oai-status-badge").textContent =
            used ? "AI 실제 사용됨" : "AI 미사용";

        el("oai-status-sub").textContent =
            ai.engine || "Orange Neural Network";

        el("oai-used").textContent =
            used ? "예" : "아니오";

        el("oai-success-rate").textContent = fmt(success);
        el("oai-coverage-rate").textContent = fmt(coverage);

        el("oai-counts").textContent =
            `${successful}/${attempted} 성공 · ${failed} 실패`;

        el("oai-probability").textContent =
            ai.selected_yes_probability_percent == null
                ? "-"
                : fmt(Number(ai.selected_yes_probability_percent));

        el("oai-prediction").textContent =
            ai.selected_prediction ?? "-";

        el("oai-success-bar").style.width =
            `${Math.max(0, Math.min(100, success))}%`;
    }

    window.__renderOrangeAIRecommendationStatus = renderAI;

    const originalFetch = window.fetch.bind(window);

    window.fetch = async (...args) => {
        const response = await originalFetch(...args);

        try {
            const input = args[0];
            const url =
                typeof input === "string"
                    ? input
                    : (input && input.url) || "";

            if (String(url).includes("/recommendations/auto")) {
                const cloned = response.clone();
                const data = await cloned.json();
                renderAI(data);
            }
        } catch (error) {
            console.warn("Orange AI status fetch hook:", error);
        }

        return response;
    };

    const originalOpen = XMLHttpRequest.prototype.open;
    const originalSend = XMLHttpRequest.prototype.send;

    XMLHttpRequest.prototype.open = function(method, url, ...rest) {
        this.__orangeAIUrl = String(url || "");
        return originalOpen.call(this, method, url, ...rest);
    };

    XMLHttpRequest.prototype.send = function(...args) {
        if (
            this.__orangeAIUrl &&
            this.__orangeAIUrl.includes("/recommendations/auto")
        ) {
            this.addEventListener("load", () => {
                try {
                    const data = JSON.parse(this.responseText);
                    renderAI(data);
                } catch (error) {
                    console.warn("Orange AI status xhr hook:", error);
                }
            });
        }

        return originalSend.apply(this, args);
    };
})();
</script>
"""


@app.middleware("http")
async def _inject_orange_ai_recommend_status(request, call_next):
    response = await call_next(request)

    if request.url.path != "/recommend":
        return response

    if response.status_code != 200:
        return response

    content_type = response.headers.get("content-type", "")
    if "text/html" not in content_type.lower():
        return response

    body = b""
    async for chunk in response.body_iterator:
        body += chunk

    try:
        html = body.decode("utf-8")
    except UnicodeDecodeError:
        return _OrangeAIStatusResponse(
            content=body,
            status_code=response.status_code,
            headers={
                key: value
                for key, value in response.headers.items()
                if key.lower() != "content-length"
            },
        )

    if "orange-ai-recommend-status-script" not in html:
        if "</body>" in html:
            html = html.replace(
                "</body>",
                _ORANGE_AI_RECOMMEND_STATUS_UI + "</body>",
                1,
            )
        else:
            html += _ORANGE_AI_RECOMMEND_STATUS_UI

    headers = {
        key: value
        for key, value in response.headers.items()
        if key.lower() not in {
            "content-length",
            "content-type",
        }
    }

    return _OrangeAIStatusResponse(
        content=html,
        status_code=response.status_code,
        headers=headers,
        media_type="text/html",
    )
# ORANGE_AI_RECOMMEND_PAGE_STATUS_END
