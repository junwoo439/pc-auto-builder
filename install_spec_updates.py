
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path.cwd()
PACKAGE_ROOT = Path(__file__).resolve().parent

MAIN = ROOT / "backend" / "app" / "main.py"
ADMIN = ROOT / "frontend" / "admin.html"

SERVICE_SOURCE = (
    PACKAGE_ROOT
    / "backend"
    / "app"
    / "services"
    / "danawa_spec_updater.py"
)

ROUTER_SOURCE = (
    PACKAGE_ROOT
    / "backend"
    / "app"
    / "routers"
    / "spec_updates.py"
)

SERVICE_TARGET = (
    ROOT
    / "backend"
    / "app"
    / "services"
    / "danawa_spec_updater.py"
)

ROUTER_TARGET = (
    ROOT
    / "backend"
    / "app"
    / "routers"
    / "spec_updates.py"
)


def backup(path: Path) -> None:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = path.with_suffix(
        path.suffix + f".bak-{stamp}"
    )
    shutil.copy2(path, target)
    print(f"백업 생성: {target}")


def copy_files() -> None:
    SERVICE_TARGET.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    ROUTER_TARGET.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        SERVICE_SOURCE,
        SERVICE_TARGET,
    )

    shutil.copy2(
        ROUTER_SOURCE,
        ROUTER_TARGET,
    )

    print("서비스와 라우터 파일 복사 완료")


def patch_main() -> None:
    backup(MAIN)

    content = MAIN.read_text(
        encoding="utf-8-sig"
    )

    if "    spec_updates,\n" not in content:
        content = content.replace(
            "from app.routers import (\n",
            (
                "from app.routers import (\n"
                "    spec_updates,\n"
            ),
            1,
        )

    router_line = (
        "app.include_router("
        "spec_updates.router"
        ")"
    )

    if router_line not in content:
        anchor = (
            "app.include_router("
            "parts.router"
            ")\n"
        )

        if anchor not in content:
            raise RuntimeError(
                "main.py에서 parts 라우터 "
                "등록 위치를 찾지 못했습니다."
            )

        content = content.replace(
            anchor,
            anchor + router_line + "\n",
            1,
        )

    MAIN.write_text(
        content,
        encoding="utf-8",
    )

    print("main.py 패치 완료")


def patch_admin() -> None:
    backup(ADMIN)

    content = ADMIN.read_text(
        encoding="utf-8-sig"
    )

    if (
        "update-selected-specs-button"
        not in content
    ):
        anchor = '''
                <button
                    id="download-all-button"
'''

        buttons = '''
                <button
                    id="update-selected-specs-button"
                    type="button"
                >
                    선택 부품 상세 규격 갱신
                </button>

                <button
                    id="update-all-specs-button"
                    class="success"
                    type="button"
                >
                    전체 부품 상세 규격 갱신
                </button>

'''

        if anchor not in content:
            raise RuntimeError(
                "admin.html에서 전체 다운로드 "
                "버튼을 찾지 못했습니다."
            )

        content = content.replace(
            anchor,
            buttons + anchor,
            1,
        )

    if "spec-update-status" not in content:
        anchor = '''
            <div class="table-wrapper">
'''

        status_html = '''
            <div
                id="spec-update-status"
                style="
                    margin: 16px 0;
                    padding: 14px;
                    border-radius: 8px;
                    background: #eff6ff;
                    line-height: 1.7;
                    white-space: pre-wrap;
                "
                hidden
            ></div>

'''

        if anchor not in content:
            raise RuntimeError(
                "admin.html에서 부품 표 위치를 "
                "찾지 못했습니다."
            )

        content = content.replace(
            anchor,
            status_html + anchor,
            1,
        )

    if "async function runSpecUpdate" not in content:
        anchor = '''
        selectAll.addEventListener(
'''

        functions = r'''
        function showSpecUpdateStatus(
            message
        ) {
            const status =
                document.getElementById(
                    "spec-update-status"
                );

            status.hidden = false;
            status.textContent = message;
        }

        async function runSpecUpdate(
            mode
        ) {
            const adminKey = getAdminKey();

            if (!adminKey) {
                return;
            }

            if (
                mode === "selected"
                && selectedIds.size === 0
            ) {
                alert("갱신할 부품을 선택하세요.");
                return;
            }

            const selectedButton =
                document.getElementById(
                    "update-selected-specs-button"
                );

            const allButton =
                document.getElementById(
                    "update-all-specs-button"
                );

            selectedButton.disabled = true;
            allButton.disabled = true;

            showSpecUpdateStatus(
                "상세 규격을 갱신하고 있습니다.\n"
                + "전체 갱신은 약 1~3분 걸릴 수 있습니다."
            );

            const url = (
                mode === "selected"
                    ? "/spec-updates/selected"
                    : "/spec-updates/all"
            );

            const options = {
                method: "POST",

                headers: {
                    "X-Admin-Key": adminKey
                }
            };

            if (mode === "selected") {
                options.headers[
                    "Content-Type"
                ] = "application/json";

                options.body = JSON.stringify({
                    part_ids: [
                        ...selectedIds
                    ]
                });
            }

            try {
                const response = await fetch(
                    url,
                    options
                );

                if (!response.ok) {
                    throw new Error(
                        await readError(response)
                    );
                }

                const data = await response.json();

                const errorText = (
                    Array.isArray(data.errors)
                    && data.errors.length > 0
                )
                    ? (
                        "\n최근 오류: "
                        + data.errors[0].message
                    )
                    : "";

                showSpecUpdateStatus(
                    [
                        `전체: ${data.total}개`,
                        `갱신 성공: ${data.updated}개`,
                        `실패: ${data.failed}개`,
                        (
                            "시드 자동 저장: "
                            + (
                                data.seed_saved
                                    ? "완료"
                                    : "실패"
                            )
                        )
                    ].join("\n")
                    + errorText
                );

                await loadParts();

            } catch (error) {
                showSpecUpdateStatus(
                    "오류: " + error.message
                );

            } finally {
                selectedButton.disabled = false;
                allButton.disabled = false;
            }
        }

'''

        if anchor not in content:
            raise RuntimeError(
                "admin.html에서 이벤트 등록 "
                "위치를 찾지 못했습니다."
            )

        content = content.replace(
            anchor,
            functions + anchor,
            1,
        )

    listener_marker = (
        "runSpecUpdate(\n"
        '                "selected"'
    )

    if listener_marker not in content:
        anchor = '''
        resetForm();
        loadParts();
'''

        listeners = '''
        document.getElementById(
            "update-selected-specs-button"
        ).addEventListener(
            "click",
            () => runSpecUpdate(
                "selected"
            )
        );

        document.getElementById(
            "update-all-specs-button"
        ).addEventListener(
            "click",
            () => runSpecUpdate(
                "all"
            )
        );

'''

        if anchor not in content:
            raise RuntimeError(
                "admin.html에서 초기 실행 위치를 "
                "찾지 못했습니다."
            )

        content = content.replace(
            anchor,
            listeners + anchor,
            1,
        )

    ADMIN.write_text(
        content,
        encoding="utf-8",
    )

    print("admin.html 패치 완료")


def main() -> None:
    if not MAIN.exists():
        raise SystemExit(
            "pc-auto-builder 프로젝트의 "
            "최상위 폴더에서 실행하세요."
        )

    if not ADMIN.exists():
        raise SystemExit(
            "frontend/admin.html을 찾지 못했습니다."
        )

    copy_files()
    patch_main()
    patch_admin()

    print()
    print("설치 완료")
    print(
        "이제 backend 폴더에서 문법 검사를 "
        "실행하세요."
    )


if __name__ == "__main__":
    main()
