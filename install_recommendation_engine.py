from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = ROOT / "recommendation_engine_files"

TARGETS = {
    SOURCE_ROOT
    / "backend"
    / "app"
    / "routers"
    / "recommendations.py": (
        Path("backend")
        / "app"
        / "routers"
        / "recommendations.py"
    ),
    SOURCE_ROOT
    / "frontend"
    / "recommend.html": (
        Path("frontend")
        / "recommend.html"
    ),
}


def find_project_root() -> Path:
    candidates = [
        ROOT,
        Path.cwd(),
    ]

    for candidate in candidates:
        if (
            (candidate / "backend" / "app" / "main.py").exists()
            and (candidate / "frontend").is_dir()
        ):
            return candidate

    raise SystemExit(
        "프로젝트 최상위 폴더에서 실행하세요. "
        "backend/app/main.py를 찾지 못했습니다."
    )


def backup_and_copy(
    project_root: Path,
    source: Path,
    relative_target: Path,
    timestamp: str,
) -> None:
    if not source.exists():
        raise FileNotFoundError(
            f"설치 파일을 찾지 못했습니다: {source}"
        )

    target = project_root / relative_target
    target.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if target.exists():
        backup = target.with_name(
            f"{target.name}.before_auto_recommend_{timestamp}"
        )
        shutil.copy2(target, backup)
        print(f"백업: {backup}")

    shutil.copy2(source, target)
    print(f"설치: {target}")


def run_checks(project_root: Path) -> None:
    backend = project_root / "backend"

    compile_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "compileall",
            "-q",
            "app",
        ],
        cwd=backend,
        check=False,
    )

    if compile_result.returncode != 0:
        raise SystemExit(
            "Python 문법 검사에 실패했습니다. "
            "위 오류 내용을 확인하세요."
        )

    route_result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from app.main import app; "
                "print('/recommendations/auto' "
                "in app.openapi()['paths'])"
            ),
        ],
        cwd=backend,
        check=False,
        capture_output=True,
        text=True,
    )

    if route_result.returncode != 0:
        print(route_result.stdout)
        print(route_result.stderr)
        raise SystemExit(
            "FastAPI 라우터 확인에 실패했습니다."
        )

    route_value = route_result.stdout.strip().splitlines()
    route_value = route_value[-1] if route_value else ""

    if route_value != "True":
        raise SystemExit(
            "추천 API가 등록되지 않았습니다. "
            "backend/app/main.py에서 recommendations.router를 "
            "등록했는지 확인하세요."
        )

    print("검사: Python 문법 정상")
    print("검사: /recommendations/auto 등록 정상")


def main() -> None:
    project_root = find_project_root()
    timestamp = datetime.now().strftime(
        "%Y%m%d-%H%M%S"
    )

    for source, relative_target in TARGETS.items():
        backup_and_copy(
            project_root,
            source,
            relative_target,
            timestamp,
        )

    run_checks(project_root)

    print()
    print("자동 추천 엔진 설치 완료")
    print("서버 실행:")
    print(
        "  cd backend"
    )
    print(
        "  .\\.venv\\Scripts\\python.exe "
        "-m uvicorn app.main:app --reload"
    )
    print("추천 화면:")
    print("  http://127.0.0.1:8000/recommend")


if __name__ == "__main__":
    main()
