from __future__ import annotations

import py_compile
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = ROOT / "bulk_import_limit_files"

FILES = [
    (
        SOURCE_ROOT / "backend/app/routers/imports.py",
        ROOT / "backend/app/routers/imports.py",
    ),
    (
        SOURCE_ROOT / "frontend/bulk-import.html",
        ROOT / "frontend/bulk-import.html",
    ),
]


def backup_file(path: Path) -> Path | None:
    if not path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_name(f"{path.name}.before_bulk_limit_{timestamp}.bak")
    shutil.copy2(path, backup)
    return backup


def same_file(source: Path, target: Path) -> bool:
    try:
        return source.resolve() == target.resolve()
    except OSError:
        return False


def install_file(source: Path, target: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"설치 원본 파일이 없습니다: {source}")

    target.parent.mkdir(parents=True, exist_ok=True)

    if same_file(source, target):
        print(f"건너뜀(이미 같은 위치): {target}")
        return

    backup = backup_file(target)
    if backup is not None:
        print(f"백업: {backup}")

    shutil.copy2(source, target)
    print(f"설치: {target}")


def verify() -> None:
    imports_path = ROOT / "backend/app/routers/imports.py"
    html_path = ROOT / "frontend/bulk-import.html"

    py_compile.compile(
        str(imports_path),
        doraise=True,
    )

    imports_text = imports_path.read_text(encoding="utf-8-sig")
    html_text = html_path.read_text(encoding="utf-8-sig")

    required_imports = [
        "default=20",
        "le=100",
        "default=500",
        "le=1000",
    ]
    required_html = [
        'max="100"',
        'value="20"',
        'max="1000"',
        'value="500"',
        "maxPages > 100",
        "maxProducts > 1000",
    ]

    for marker in required_imports:
        if marker not in imports_text:
            raise RuntimeError(
                f"백엔드 적용 확인 실패: {marker}"
            )

    for marker in required_html:
        if marker not in html_text:
            raise RuntimeError(
                f"프런트엔드 적용 확인 실패: {marker}"
            )

    print("검사: Python 문법 정상")
    print("검사: 최대 100페이지 / 1,000상품 적용 정상")


def main() -> None:
    if not (ROOT / "backend").exists() or not (ROOT / "frontend").exists():
        raise SystemExit(
            "이 설치 파일을 pc-auto-builder 프로젝트 최상위에서 실행하세요."
        )

    for source, target in FILES:
        install_file(source, target)

    verify()

    print()
    print("대량 수집 제한 확장 설치 완료")
    print("기본값: 20페이지 / 500상품")
    print("최대값: 100페이지 / 1,000상품")


if __name__ == "__main__":
    main()
