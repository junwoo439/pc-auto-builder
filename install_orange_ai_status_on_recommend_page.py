from __future__ import annotations

from pathlib import Path
from datetime import datetime
import shutil
import py_compile

MARKER = "# ORANGE_AI_RECOMMEND_PAGE_STATUS_BEGIN"
MIDDLEWARE = '# ORANGE_AI_RECOMMEND_PAGE_STATUS_BEGIN\n# /recommend 화면에 자동 추천의 Orange AI 실제 사용 여부와 실행률을 표시합니다.\nfrom starlette.responses import Response as _OrangeAIStatusResponse\n\n_ORANGE_AI_RECOMMEND_STATUS_UI = r"""\n<style id="orange-ai-recommend-status-style">\n#orange-ai-recommend-status {\n    box-sizing: border-box;\n    position: fixed;\n    right: 20px;\n    bottom: 20px;\n    z-index: 99999;\n    width: min(390px, calc(100vw - 32px));\n    padding: 16px;\n    border: 1px solid rgba(127,127,127,.28);\n    border-radius: 16px;\n    background: rgba(20, 22, 28, .96);\n    color: #f5f7fb;\n    box-shadow: 0 14px 40px rgba(0,0,0,.28);\n    font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;\n    line-height: 1.45;\n}\n#orange-ai-recommend-status .oai-head {\n    display:flex;\n    align-items:center;\n    justify-content:space-between;\n    gap:12px;\n    margin-bottom:10px;\n}\n#orange-ai-recommend-status .oai-title {\n    font-size:16px;\n    font-weight:800;\n}\n#orange-ai-recommend-status .oai-badge {\n    padding:4px 8px;\n    border-radius:999px;\n    background:#323744;\n    font-size:12px;\n    font-weight:700;\n    white-space:nowrap;\n}\n#orange-ai-recommend-status[data-active="true"] .oai-badge {\n    background:#153f2d;\n}\n#orange-ai-recommend-status[data-active="false"] .oai-badge {\n    background:#4a2b2b;\n}\n#orange-ai-recommend-status .oai-sub {\n    color:#b9c0cc;\n    font-size:12px;\n    margin-bottom:12px;\n}\n#orange-ai-recommend-status .oai-grid {\n    display:grid;\n    grid-template-columns:1fr auto;\n    gap:7px 12px;\n    font-size:13px;\n}\n#orange-ai-recommend-status .oai-grid strong {\n    text-align:right;\n}\n#orange-ai-recommend-status .oai-bar {\n    height:8px;\n    border-radius:999px;\n    background:#353945;\n    overflow:hidden;\n    margin-top:8px;\n}\n#orange-ai-recommend-status .oai-bar > span {\n    display:block;\n    height:100%;\n    width:0%;\n    background:linear-gradient(90deg,#5b8cff,#7bd3a8);\n    transition:width .3s ease;\n}\n#orange-ai-recommend-status .oai-note {\n    margin-top:10px;\n    color:#9fa7b5;\n    font-size:11px;\n}\n@media (max-width: 700px) {\n    #orange-ai-recommend-status {\n        position:static;\n        width:auto;\n        margin:16px;\n    }\n}\n</style>\n\n<section id="orange-ai-recommend-status" data-active="waiting">\n    <div class="oai-head">\n        <div class="oai-title">🤖 Orange AI 자동 추천</div>\n        <div class="oai-badge" id="oai-status-badge">대기 중</div>\n    </div>\n    <div class="oai-sub" id="oai-status-sub">\n        자동 추천을 실행하면 실제 AI 사용 여부와 실행률이 표시됩니다.\n    </div>\n    <div class="oai-grid">\n        <span>최종 순위에 AI 사용</span><strong id="oai-used">-</strong>\n        <span>AI 실행 성공률</span><strong id="oai-success-rate">-</strong>\n        <span>전체 후보 AI 적용률</span><strong id="oai-coverage-rate">-</strong>\n        <span>AI 실행 횟수</span><strong id="oai-counts">-</strong>\n        <span>선택 조합 AI 호환 확률</span><strong id="oai-probability">-</strong>\n        <span>AI 최종 판정</span><strong id="oai-prediction">-</strong>\n    </div>\n    <div class="oai-bar" title="AI 실행 성공률">\n        <span id="oai-success-bar"></span>\n    </div>\n    <div class="oai-note">\n        실행 성공률 = 정상 AI 추론 수 ÷ AI 추론 시도 수 × 100\n    </div>\n</section>\n\n<script id="orange-ai-recommend-status-script">\n(() => {\n    const card = document.getElementById("orange-ai-recommend-status");\n    if (!card) return;\n\n    const el = (id) => document.getElementById(id);\n    const fmt = (v) => (\n        typeof v === "number" && Number.isFinite(v)\n            ? `${v.toFixed(1)}%`\n            : "-"\n    );\n\n    function renderAI(data) {\n        const ai = data && data.ai;\n\n        if (!ai) {\n            card.dataset.active = "false";\n            el("oai-status-badge").textContent = "AI 정보 없음";\n            el("oai-status-sub").textContent =\n                "자동 추천 응답에 ai 정보가 없습니다. recommendations.py의 Orange AI 패치를 확인하세요.";\n            return;\n        }\n\n        const used = ai.used_in_ranking === true;\n        const success = Number(ai.execution_success_rate_percent ?? 0);\n        const coverage = Number(ai.coverage_rate_percent ?? 0);\n        const attempted = Number(ai.attempted_candidates ?? 0);\n        const successful = Number(ai.successful_candidates ?? 0);\n        const failed = Number(ai.failed_candidates ?? 0);\n\n        card.dataset.active = String(used);\n        el("oai-status-badge").textContent =\n            used ? "AI 실제 사용됨" : "AI 미사용";\n\n        el("oai-status-sub").textContent =\n            ai.engine || "Orange Neural Network";\n\n        el("oai-used").textContent =\n            used ? "예" : "아니오";\n\n        el("oai-success-rate").textContent = fmt(success);\n        el("oai-coverage-rate").textContent = fmt(coverage);\n\n        el("oai-counts").textContent =\n            `${successful}/${attempted} 성공 · ${failed} 실패`;\n\n        el("oai-probability").textContent =\n            ai.selected_yes_probability_percent == null\n                ? "-"\n                : fmt(Number(ai.selected_yes_probability_percent));\n\n        el("oai-prediction").textContent =\n            ai.selected_prediction ?? "-";\n\n        el("oai-success-bar").style.width =\n            `${Math.max(0, Math.min(100, success))}%`;\n    }\n\n    window.__renderOrangeAIRecommendationStatus = renderAI;\n\n    const originalFetch = window.fetch.bind(window);\n\n    window.fetch = async (...args) => {\n        const response = await originalFetch(...args);\n\n        try {\n            const input = args[0];\n            const url =\n                typeof input === "string"\n                    ? input\n                    : (input && input.url) || "";\n\n            if (String(url).includes("/recommendations/auto")) {\n                const cloned = response.clone();\n                const data = await cloned.json();\n                renderAI(data);\n            }\n        } catch (error) {\n            console.warn("Orange AI status fetch hook:", error);\n        }\n\n        return response;\n    };\n\n    const originalOpen = XMLHttpRequest.prototype.open;\n    const originalSend = XMLHttpRequest.prototype.send;\n\n    XMLHttpRequest.prototype.open = function(method, url, ...rest) {\n        this.__orangeAIUrl = String(url || "");\n        return originalOpen.call(this, method, url, ...rest);\n    };\n\n    XMLHttpRequest.prototype.send = function(...args) {\n        if (\n            this.__orangeAIUrl &&\n            this.__orangeAIUrl.includes("/recommendations/auto")\n        ) {\n            this.addEventListener("load", () => {\n                try {\n                    const data = JSON.parse(this.responseText);\n                    renderAI(data);\n                } catch (error) {\n                    console.warn("Orange AI status xhr hook:", error);\n                }\n            });\n        }\n\n        return originalSend.apply(this, args);\n    };\n})();\n</script>\n"""\n\n\n@app.middleware("http")\nasync def _inject_orange_ai_recommend_status(request, call_next):\n    response = await call_next(request)\n\n    if request.url.path != "/recommend":\n        return response\n\n    if response.status_code != 200:\n        return response\n\n    content_type = response.headers.get("content-type", "")\n    if "text/html" not in content_type.lower():\n        return response\n\n    body = b""\n    async for chunk in response.body_iterator:\n        body += chunk\n\n    try:\n        html = body.decode("utf-8")\n    except UnicodeDecodeError:\n        return _OrangeAIStatusResponse(\n            content=body,\n            status_code=response.status_code,\n            headers={\n                key: value\n                for key, value in response.headers.items()\n                if key.lower() != "content-length"\n            },\n        )\n\n    if "orange-ai-recommend-status-script" not in html:\n        if "</body>" in html:\n            html = html.replace(\n                "</body>",\n                _ORANGE_AI_RECOMMEND_STATUS_UI + "</body>",\n                1,\n            )\n        else:\n            html += _ORANGE_AI_RECOMMEND_STATUS_UI\n\n    headers = {\n        key: value\n        for key, value in response.headers.items()\n        if key.lower() not in {\n            "content-length",\n            "content-type",\n        }\n    }\n\n    return _OrangeAIStatusResponse(\n        content=html,\n        status_code=response.status_code,\n        headers=headers,\n        media_type="text/html",\n    )\n# ORANGE_AI_RECOMMEND_PAGE_STATUS_END'


def find_main() -> Path:
    cwd = Path.cwd()
    options = [
        cwd / "backend" / "app" / "main.py",
        cwd / "app" / "main.py",
    ]
    for path in options:
        if path.exists():
            return path
    raise SystemExit(
        "app/main.py를 찾지 못했습니다. 프로젝트 루트 또는 backend 폴더에서 실행하세요."
    )


def main() -> None:
    path = find_main()
    print("대상:", path)

    text = path.read_text(encoding="utf-8-sig")

    if MARKER in text:
        print("이미 /recommend AI 상태 표시 패치가 적용되어 있습니다.")
        return

    if "FastAPI" not in text:
        raise SystemExit("main.py에서 FastAPI 앱을 확인하지 못했습니다.")

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"main.py.backup-ai-ui-{timestamp}")
    shutil.copy2(path, backup)
    print("백업:", backup)

    text = text.rstrip() + "\n\n" + MIDDLEWARE + "\n"
    path.write_text(text, encoding="utf-8")

    try:
        py_compile.compile(str(path), doraise=True)
    except Exception:
        shutil.copy2(backup, path)
        print("문법 검사 실패 → main.py 자동 복구")
        raise

    print("문법 검사: OK")
    print()
    print("완료.")
    print("서버를 다시 실행한 뒤:")
    print("  http://127.0.0.1:8000/recommend")
    print("에서 자동 추천을 실행하세요.")
    print()
    print("표시 항목:")
    print("  Orange AI 실제 사용 여부")
    print("  AI 실행 성공률")
    print("  전체 후보 AI 적용률")
    print("  성공/시도/실패 횟수")
    print("  선택 조합 AI 호환 확률")
    print("  AI 최종 yes/no 판정")


if __name__ == "__main__":
    main()
