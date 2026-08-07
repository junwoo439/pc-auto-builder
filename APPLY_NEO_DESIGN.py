from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"

if not (FRONTEND / "index.html").exists():
    raise SystemExit(
        "[오류] APPLY_NEO_DESIGN.py를 프로젝트 최상위 폴더에 넣어주세요.\n"
        "예: C:\\Users\\windows\\Documents\\pc-auto-builder-main\\APPLY_NEO_DESIGN.py"
    )

stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
backup_dir = ROOT / f"design-backup-{stamp}"
backup_dir.mkdir(parents=True, exist_ok=False)

for html_file in FRONTEND.glob("*.html"):
    shutil.copy2(html_file, backup_dir / html_file.name)
for asset_name in ("neo-theme.css", "neo-theme.js"):
    asset_path = FRONTEND / asset_name
    if asset_path.exists():
        shutil.copy2(asset_path, backup_dir / asset_name)

css = r'''/* PC Auto Builder — NEO CIRCUIT UI */
:root {
    color-scheme: dark;
    --neo-bg: #05070d;
    --neo-bg-2: #090d18;
    --neo-panel: rgba(13, 19, 33, 0.80);
    --neo-panel-solid: #0d1321;
    --neo-panel-2: rgba(20, 28, 47, 0.82);
    --neo-line: rgba(130, 161, 255, 0.18);
    --neo-line-strong: rgba(70, 235, 255, 0.44);
    --neo-text: #eef5ff;
    --neo-muted: #93a4bd;
    --neo-cyan: #37e8ff;
    --neo-blue: #5b7cff;
    --neo-purple: #a66cff;
    --neo-green: #43f0ae;
    --neo-red: #ff647c;
    --neo-yellow: #ffd166;
    --neo-shadow: 0 24px 80px rgba(0, 0, 0, 0.46);
    --neo-radius: 18px;
}

* {
    box-sizing: border-box;
}

html {
    min-height: 100%;
    scroll-behavior: smooth;
    background: var(--neo-bg);
}

body.neo-ui {
    --mx: 50vw;
    --my: 20vh;
    min-height: 100vh;
    margin: 0;
    overflow-x: hidden;
    color: var(--neo-text) !important;
    font-family: Inter, Pretendard, "Noto Sans KR", "Segoe UI", Arial, sans-serif !important;
    background:
        radial-gradient(circle at var(--mx) var(--my), rgba(55, 232, 255, 0.095), transparent 25rem),
        radial-gradient(circle at 10% 5%, rgba(166, 108, 255, 0.16), transparent 34rem),
        radial-gradient(circle at 90% 16%, rgba(91, 124, 255, 0.15), transparent 32rem),
        linear-gradient(145deg, #05070d 0%, #080d18 45%, #05070d 100%) !important;
    background-attachment: fixed !important;
}

body.neo-ui::before {
    content: "";
    position: fixed;
    inset: 0;
    z-index: -2;
    pointer-events: none;
    opacity: 0.32;
    background-image:
        linear-gradient(rgba(74, 106, 160, 0.11) 1px, transparent 1px),
        linear-gradient(90deg, rgba(74, 106, 160, 0.11) 1px, transparent 1px);
    background-size: 48px 48px;
    mask-image: linear-gradient(to bottom, black, transparent 85%);
}

body.neo-ui::after {
    content: "";
    position: fixed;
    inset: 0;
    z-index: 9998;
    pointer-events: none;
    opacity: 0.035;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 180 180' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.8'/%3E%3C/svg%3E");
}

::selection {
    color: #021014;
    background: var(--neo-cyan);
}

::-webkit-scrollbar {
    width: 10px;
    height: 10px;
}

::-webkit-scrollbar-track {
    background: #070b12;
}

::-webkit-scrollbar-thumb {
    border: 2px solid #070b12;
    border-radius: 999px;
    background: linear-gradient(var(--neo-cyan), var(--neo-purple));
}

body.neo-ui a {
    color: #b9eaff;
}

body.neo-ui header {
    position: relative;
    isolation: isolate;
    overflow: hidden;
    padding: 72px 24px 58px !important;
    color: var(--neo-text) !important;
    text-align: center;
    border-bottom: 1px solid var(--neo-line);
    background:
        linear-gradient(180deg, rgba(8, 12, 23, 0.55), rgba(8, 12, 23, 0.92)),
        radial-gradient(circle at 50% -10%, rgba(55, 232, 255, 0.22), transparent 44%) !important;
}

body.neo-ui header::before {
    content: "";
    position: absolute;
    inset: auto 8% 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--neo-cyan), var(--neo-purple), transparent);
    box-shadow: 0 0 26px rgba(55, 232, 255, 0.8);
}

body.neo-ui header::after {
    content: "AI-POWERED COMPATIBILITY ENGINE";
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-top: 20px;
    padding: 7px 12px;
    border: 1px solid rgba(55, 232, 255, 0.3);
    border-radius: 999px;
    color: var(--neo-cyan);
    background: rgba(55, 232, 255, 0.07);
    font-family: Consolas, "SFMono-Regular", monospace;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.16em;
}

body.neo-ui header h1 {
    margin: 0 0 12px !important;
    font-size: clamp(2.25rem, 7vw, 4.8rem) !important;
    font-weight: 900 !important;
    line-height: 0.98 !important;
    letter-spacing: -0.055em !important;
    color: transparent !important;
    background: linear-gradient(100deg, #ffffff 3%, #9ff4ff 42%, #8ca2ff 68%, #d4a8ff 96%);
    -webkit-background-clip: text;
    background-clip: text;
    filter: drop-shadow(0 0 24px rgba(55, 232, 255, 0.18));
}

body.neo-ui header p {
    max-width: 720px;
    margin: 0 auto !important;
    color: var(--neo-muted) !important;
    font-size: clamp(0.96rem, 2vw, 1.13rem) !important;
    line-height: 1.75;
}

body.neo-ui nav,
body.neo-ui .pc-tools-navigation {
    display: flex !important;
    flex-wrap: wrap;
    align-items: center;
    justify-content: center;
    gap: 10px !important;
}

body.neo-ui > nav.pc-tools-navigation {
    position: sticky;
    top: 0;
    z-index: 1000;
    margin: 0 !important;
    padding: 13px 18px !important;
    border-bottom: 1px solid var(--neo-line);
    background: rgba(5, 8, 15, 0.78) !important;
    box-shadow: 0 12px 36px rgba(0, 0, 0, 0.24);
    backdrop-filter: blur(18px) saturate(150%);
}

body.neo-ui main > nav {
    position: sticky;
    top: 12px;
    z-index: 800;
    width: fit-content;
    max-width: 100%;
    margin: 0 auto 24px !important;
    padding: 8px !important;
    border: 1px solid var(--neo-line);
    border-radius: 16px;
    background: rgba(7, 11, 20, 0.72);
    box-shadow: 0 16px 50px rgba(0, 0, 0, 0.32);
    backdrop-filter: blur(18px);
}

body.neo-ui nav a,
body.neo-ui .pc-tools-navigation a {
    position: relative;
    overflow: hidden;
    margin: 0 !important;
    padding: 10px 15px !important;
    border: 1px solid transparent !important;
    border-radius: 11px !important;
    color: #b5c3d9 !important;
    background: transparent !important;
    text-decoration: none !important;
    font-size: 0.92rem;
    font-weight: 750 !important;
    letter-spacing: -0.01em;
    transition: color .2s ease, background .2s ease, border-color .2s ease, transform .2s ease !important;
}

body.neo-ui nav a:hover,
body.neo-ui .pc-tools-navigation a:hover {
    color: white !important;
    border-color: rgba(55, 232, 255, 0.24) !important;
    background: rgba(55, 232, 255, 0.08) !important;
    transform: translateY(-1px);
}

body.neo-ui nav a.neo-active,
body.neo-ui nav a.highlight,
body.neo-ui .pc-tools-navigation a.neo-active,
body.neo-ui .pc-tools-navigation a.highlight {
    color: #041116 !important;
    border-color: rgba(139, 249, 255, 0.72) !important;
    background: linear-gradient(120deg, var(--neo-cyan), #7fe0ff 42%, #9b8cff) !important;
    box-shadow: 0 7px 24px rgba(55, 232, 255, 0.22), inset 0 1px rgba(255, 255, 255, 0.55) !important;
}

body.neo-ui main {
    width: min(1180px, calc(100% - 32px)) !important;
    margin: 34px auto 80px !important;
}

body.neo-ui .builder,
body.neo-ui .grid,
body.neo-ui .equipment-grid {
    gap: 16px !important;
}

body.neo-ui .card,
body.neo-ui .part-card,
body.neo-ui #result,
body.neo-ui .notice,
body.neo-ui .equipment-option {
    position: relative;
    color: var(--neo-text) !important;
    border: 1px solid var(--neo-line) !important;
    border-radius: var(--neo-radius) !important;
    background: linear-gradient(145deg, rgba(20, 28, 47, 0.86), rgba(9, 14, 25, 0.84)) !important;
    box-shadow: var(--neo-shadow) !important;
    backdrop-filter: blur(16px) saturate(125%);
}

body.neo-ui .card,
body.neo-ui .part-card,
body.neo-ui #result {
    padding: 22px !important;
}

body.neo-ui .part-card,
body.neo-ui .card {
    overflow: hidden;
    transition: transform .25s ease, border-color .25s ease, box-shadow .25s ease;
}

body.neo-ui .part-card::before,
body.neo-ui .card::before {
    content: "";
    position: absolute;
    inset: 0 0 auto;
    height: 2px;
    opacity: 0.75;
    background: linear-gradient(90deg, transparent, var(--neo-cyan), var(--neo-purple), transparent);
}

body.neo-ui .part-card:hover,
body.neo-ui .card:hover {
    border-color: rgba(55, 232, 255, 0.34) !important;
    box-shadow: 0 28px 90px rgba(0, 0, 0, 0.55), 0 0 0 1px rgba(55, 232, 255, 0.07) !important;
    transform: translateY(-3px);
}

body.neo-ui h2,
body.neo-ui h3,
body.neo-ui h4 {
    color: #f6fbff !important;
    letter-spacing: -0.035em;
}

body.neo-ui label {
    color: #dce8f8 !important;
    font-weight: 750 !important;
}

body.neo-ui input:not([type="checkbox"]):not([type="radio"]),
body.neo-ui select,
body.neo-ui textarea {
    width: 100%;
    color: var(--neo-text) !important;
    border: 1px solid rgba(125, 151, 197, 0.28) !important;
    border-radius: 12px !important;
    outline: none;
    background: rgba(3, 7, 14, 0.72) !important;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.035) !important;
    transition: border-color .2s ease, box-shadow .2s ease, transform .2s ease !important;
}

body.neo-ui input::placeholder,
body.neo-ui textarea::placeholder {
    color: #65748a !important;
}

body.neo-ui input:not([type="checkbox"]):not([type="radio"]):focus,
body.neo-ui select:focus,
body.neo-ui textarea:focus {
    border-color: var(--neo-cyan) !important;
    box-shadow: 0 0 0 4px rgba(55, 232, 255, 0.11), 0 0 28px rgba(55, 232, 255, 0.08) !important;
    transform: translateY(-1px);
}

body.neo-ui select option {
    color: #eef5ff;
    background: #0c1220;
}

body.neo-ui input[type="checkbox"],
body.neo-ui input[type="radio"] {
    accent-color: var(--neo-cyan);
}

body.neo-ui button {
    position: relative;
    isolation: isolate;
    overflow: hidden;
    color: #031116 !important;
    border: 1px solid rgba(187, 252, 255, 0.62) !important;
    border-radius: 12px !important;
    background: linear-gradient(120deg, var(--neo-cyan), #75bfff 52%, #a785ff) !important;
    box-shadow: 0 12px 30px rgba(55, 232, 255, 0.18), inset 0 1px rgba(255, 255, 255, 0.5) !important;
    font-weight: 850 !important;
    letter-spacing: -0.01em;
    cursor: pointer;
    transition: transform .18s ease, box-shadow .18s ease, filter .18s ease !important;
}

body.neo-ui button:hover:not(:disabled) {
    box-shadow: 0 18px 45px rgba(55, 232, 255, 0.27), inset 0 1px rgba(255, 255, 255, 0.6) !important;
    filter: saturate(1.18) brightness(1.06);
    transform: translateY(-2px);
}

body.neo-ui button:active:not(:disabled) {
    transform: translateY(0) scale(0.985);
}

body.neo-ui button:disabled {
    color: #758399 !important;
    border-color: rgba(120, 140, 175, 0.18) !important;
    background: #161d2b !important;
    box-shadow: none !important;
    cursor: not-allowed;
}

body.neo-ui button.secondary {
    color: #dbe8fa !important;
    border-color: rgba(142, 164, 203, 0.26) !important;
    background: linear-gradient(145deg, #202b40, #151d2d) !important;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25) !important;
}

body.neo-ui button.success {
    color: #02160e !important;
    border-color: rgba(127, 255, 202, 0.5) !important;
    background: linear-gradient(120deg, #43f0ae, #8ff4c9) !important;
}

body.neo-ui button.warning {
    color: #1b1200 !important;
    border-color: rgba(255, 214, 122, 0.55) !important;
    background: linear-gradient(120deg, #ffd166, #ffad66) !important;
}

body.neo-ui button.danger {
    color: #1b0308 !important;
    border-color: rgba(255, 154, 170, 0.55) !important;
    background: linear-gradient(120deg, #ff647c, #ff9aab) !important;
}

body.neo-ui .help,
body.neo-ui .notice,
body.neo-ui #message,
body.neo-ui .summary,
body.neo-ui .selection-info,
body.neo-ui .field-help {
    color: #c4d3e8 !important;
    border: 1px solid rgba(55, 232, 255, 0.17) !important;
    border-radius: 13px !important;
    background: rgba(55, 232, 255, 0.055) !important;
}

body.neo-ui .help,
body.neo-ui .notice,
body.neo-ui #message,
body.neo-ui .summary {
    padding: 14px !important;
}

body.neo-ui .equipment-option {
    box-shadow: none !important;
    cursor: pointer;
    transition: transform .2s ease, border-color .2s ease, background .2s ease !important;
}

body.neo-ui .equipment-option:hover {
    border-color: rgba(55, 232, 255, 0.34) !important;
    transform: translateY(-2px);
}

body.neo-ui .equipment-option:has(input:checked) {
    border-color: var(--neo-cyan) !important;
    background: linear-gradient(145deg, rgba(55, 232, 255, 0.15), rgba(166, 108, 255, 0.10)) !important;
    box-shadow: inset 0 0 0 1px rgba(55, 232, 255, 0.08) !important;
}

body.neo-ui .price,
body.neo-ui .viz-stat,
body.neo-ui strong {
    color: #f5fbff;
}

body.neo-ui .price {
    color: var(--neo-cyan) !important;
    text-shadow: 0 0 20px rgba(55, 232, 255, 0.28);
}

body.neo-ui .success-text,
body.neo-ui .success {
    color: var(--neo-green);
}

body.neo-ui .failure-text,
body.neo-ui .error,
body.neo-ui .danger-text {
    color: var(--neo-red);
}

body.neo-ui #result.success {
    border-left: 4px solid var(--neo-green) !important;
}

body.neo-ui #result.failure,
body.neo-ui #message.error {
    border-left: 4px solid var(--neo-red) !important;
    background: rgba(255, 100, 124, 0.07) !important;
}

body.neo-ui .table-wrapper {
    overflow: auto;
    border: 1px solid var(--neo-line);
    border-radius: 15px;
    background: rgba(5, 8, 15, 0.52);
}

body.neo-ui table {
    width: 100%;
    color: var(--neo-text) !important;
    border-collapse: collapse;
    background: transparent !important;
}

body.neo-ui th {
    position: sticky;
    top: 0;
    z-index: 3;
    color: #9fefff !important;
    border-color: var(--neo-line) !important;
    background: rgba(10, 16, 28, 0.96) !important;
    backdrop-filter: blur(12px);
}

body.neo-ui td {
    color: #c8d5e8 !important;
    border-color: rgba(128, 153, 196, 0.12) !important;
    background: transparent !important;
}

body.neo-ui tbody tr {
    transition: background .18s ease;
}

body.neo-ui tbody tr:hover {
    background: rgba(55, 232, 255, 0.05) !important;
}

body.neo-ui code,
body.neo-ui pre {
    color: #b8f7ff;
    border: 1px solid rgba(55, 232, 255, 0.15);
    border-radius: 10px;
    background: rgba(2, 5, 11, 0.78);
    font-family: Consolas, "SFMono-Regular", monospace;
}

.neo-status-chip {
    position: fixed;
    right: 16px;
    bottom: 16px;
    z-index: 1100;
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 10px 13px;
    color: #b8c8db;
    border: 1px solid var(--neo-line);
    border-radius: 999px;
    background: rgba(5, 9, 17, 0.78);
    box-shadow: 0 16px 48px rgba(0, 0, 0, 0.42);
    backdrop-filter: blur(16px);
    font-family: Consolas, "SFMono-Regular", monospace;
    font-size: 11px;
    letter-spacing: 0.06em;
    pointer-events: none;
}

.neo-status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--neo-green);
    box-shadow: 0 0 12px var(--neo-green);
    animation: neoPulse 1.8s ease-in-out infinite;
}

.neo-ripple {
    position: absolute;
    z-index: -1;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.62);
    pointer-events: none;
    transform: translate(-50%, -50%) scale(0);
    animation: neoRipple .55s ease-out forwards;
}

.neo-reveal {
    opacity: 0;
    transform: translateY(18px);
}

.neo-reveal.neo-visible {
    opacity: 1;
    transform: none;
    transition: opacity .55s ease, transform .55s cubic-bezier(.2,.8,.2,1);
}

@keyframes neoPulse {
    0%, 100% { opacity: .65; transform: scale(.9); }
    50% { opacity: 1; transform: scale(1.16); }
}

@keyframes neoRipple {
    to { opacity: 0; transform: translate(-50%, -50%) scale(28); }
}

@media (max-width: 720px) {
    body.neo-ui header {
        padding: 54px 18px 44px !important;
    }

    body.neo-ui header h1 {
        font-size: clamp(2.05rem, 12vw, 3.25rem) !important;
    }

    body.neo-ui main {
        width: min(100% - 20px, 1180px) !important;
        margin-top: 20px !important;
    }

    body.neo-ui .card,
    body.neo-ui .part-card,
    body.neo-ui #result {
        padding: 17px !important;
        border-radius: 15px !important;
    }

    body.neo-ui main > nav {
        position: static;
        width: 100%;
    }

    body.neo-ui nav a,
    body.neo-ui .pc-tools-navigation a {
        flex: 1 1 auto;
        padding: 9px 10px !important;
        text-align: center;
        font-size: .84rem;
    }

    .neo-status-chip {
        right: 10px;
        bottom: 10px;
        font-size: 10px;
    }
}

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        scroll-behavior: auto !important;
        animation-duration: .001ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: .001ms !important;
    }
}
'''

js = r'''(() => {
    "use strict";

    const pageLabels = {
        "/": "직접 견적",
        "/app": "직접 견적",
        "/recommend": "AI 자동 추천",
        "/admin": "부품 관리",
        "/import": "URL 가져오기",
        "/bulk-import": "대량 수집",
        "/backup": "백업 관리"
    };

    const normalizePath = (href) => {
        try {
            const url = new URL(href, window.location.origin);
            return url.pathname.replace(/\/$/, "") || "/";
        } catch {
            return "";
        }
    };

    const currentPath = window.location.pathname.replace(/\/$/, "") || "/";
    document.body.classList.add("neo-ui");

    document.querySelectorAll("nav a").forEach((link) => {
        const path = normalizePath(link.getAttribute("href") || "");
        const rawText = (link.textContent || "").trim();

        if (pageLabels[path] && (!rawText || rawText.includes("?") || rawText.includes("�"))) {
            link.textContent = pageLabels[path];
        }

        link.classList.remove("highlight");
        if (path === currentPath || (currentPath === "/" && path === "/app")) {
            link.classList.add("neo-active");
            link.setAttribute("aria-current", "page");
        }
    });

    const statusChip = document.createElement("div");
    statusChip.className = "neo-status-chip";
    statusChip.setAttribute("aria-hidden", "true");
    statusChip.innerHTML = '<span class="neo-status-dot"></span><span>LOCAL ENGINE ONLINE</span>';
    document.body.appendChild(statusChip);

    let pointerFrame = 0;
    window.addEventListener("pointermove", (event) => {
        if (pointerFrame) return;
        pointerFrame = window.requestAnimationFrame(() => {
            document.body.style.setProperty("--mx", `${event.clientX}px`);
            document.body.style.setProperty("--my", `${event.clientY}px`);
            pointerFrame = 0;
        });
    }, { passive: true });

    document.querySelectorAll("button").forEach((button) => {
        button.addEventListener("pointerdown", (event) => {
            if (button.disabled) return;
            const rect = button.getBoundingClientRect();
            const ripple = document.createElement("span");
            ripple.className = "neo-ripple";
            ripple.style.left = `${event.clientX - rect.left}px`;
            ripple.style.top = `${event.clientY - rect.top}px`;
            button.appendChild(ripple);
            window.setTimeout(() => ripple.remove(), 650);
        });
    });

    const revealTargets = document.querySelectorAll(".card, .part-card, #result");
    if ("IntersectionObserver" in window) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return;
                entry.target.classList.add("neo-visible");
                observer.unobserve(entry.target);
            });
        }, { threshold: 0.08 });

        revealTargets.forEach((element, index) => {
            element.classList.add("neo-reveal");
            element.style.transitionDelay = `${Math.min(index * 45, 260)}ms`;
            observer.observe(element);
        });
    } else {
        revealTargets.forEach((element) => element.classList.add("neo-visible"));
    }
})();
'''

(FRONTEND / "neo-theme.css").write_text(css, encoding="utf-8")
(FRONTEND / "neo-theme.js").write_text(js, encoding="utf-8")

version = datetime.now().strftime("%Y%m%d%H%M%S")
css_tag = f'    <link rel="stylesheet" href="/static/neo-theme.css?v={version}">'
js_tag = f'    <script src="/static/neo-theme.js?v={version}"></script>'

targets = [
    "index.html",
    "recommend.html",
    "admin.html",
    "import.html",
    "bulk-import.html",
    "backup.html",
]

for name in targets:
    path = FRONTEND / name
    if not path.exists():
        print(f"[건너뜀] {name}: 파일 없음")
        continue

    html = path.read_text(encoding="utf-8-sig")
    html = re.sub(
        r"\s*<link[^>]+href=[\"'][^\"']*neo-theme\.css[^\"']*[\"'][^>]*>",
        "",
        html,
        flags=re.IGNORECASE,
    )
    html = re.sub(
        r"\s*<script[^>]+src=[\"'][^\"']*neo-theme\.js[^\"']*[\"'][^>]*>\s*</script>",
        "",
        html,
        flags=re.IGNORECASE,
    )

    if "</head>" not in html.lower() or "</body>" not in html.lower():
        print(f"[건너뜀] {name}: HTML 구조 확인 필요")
        continue

    html = re.sub(r"</head>", css_tag + "\n</head>", html, count=1, flags=re.IGNORECASE)
    html = re.sub(r"</body>", js_tag + "\n</body>", html, count=1, flags=re.IGNORECASE)
    path.write_text(html, encoding="utf-8")
    print(f"[적용 완료] {name}")

print("\n" + "=" * 62)
print("NEO CIRCUIT 디자인 적용 완료")
print(f"원본 백업: {backup_dir}")
print("서버가 켜져 있으면 브라우저에서 Ctrl + F5를 눌러 새로고침하세요.")
print("접속 주소: http://127.0.0.1:8000/app")
print("=" * 62)
