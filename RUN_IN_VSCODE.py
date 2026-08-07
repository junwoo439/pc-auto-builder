from __future__ import annotations

import hashlib
import os
import secrets
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"
REQUIREMENTS = BACKEND_DIR / "requirements.txt"
VENV_DIR = PROJECT_ROOT / ".venv"
VENV_PYTHON = (
    VENV_DIR / "Scripts" / "python.exe"
    if os.name == "nt"
    else VENV_DIR / "bin" / "python"
)
HASH_FILE = VENV_DIR / ".pc_builder_requirements.sha256"
APP_URL = "http://127.0.0.1:8000/app"


def title(text: str) -> None:
    print("\n" + "=" * 64)
    print(text)
    print("=" * 64)


def requirements_hash() -> str:
    return hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()


def run_checked(command: list[str], cwd: Path | None = None) -> None:
    print(">", " ".join(command))
    subprocess.run(command, cwd=cwd, check=True)


def ensure_project_files() -> None:
    required = [BACKEND_DIR / "app" / "main.py", REQUIREMENTS]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "필수 프로젝트 파일을 찾을 수 없습니다:\n- " + "\n- ".join(missing)
        )


def ensure_venv() -> None:
    if VENV_PYTHON.exists():
        print("[확인] Python 가상환경이 이미 있습니다.")
        return

    title("1/3 Python 가상환경 생성")
    run_checked([sys.executable, "-m", "venv", str(VENV_DIR)])

    if not VENV_PYTHON.exists():
        raise RuntimeError("가상환경 Python 생성에 실패했습니다.")


def ensure_packages() -> None:
    current_hash = requirements_hash()
    installed_hash = HASH_FILE.read_text(encoding="utf-8").strip() if HASH_FILE.exists() else ""

    if current_hash == installed_hash:
        print("[확인] 필요한 Python 패키지가 이미 설치되어 있습니다.")
        return

    title("2/3 필요한 패키지 설치")
    run_checked([str(VENV_PYTHON), "-m", "pip", "install", "--upgrade", "pip"])
    run_checked(
        [str(VENV_PYTHON), "-m", "pip", "install", "-r", str(REQUIREMENTS)]
    )
    HASH_FILE.write_text(current_hash, encoding="utf-8")


def ensure_env() -> None:
    env_file = BACKEND_DIR / ".env"
    if env_file.exists() and "ADMIN_API_KEY=" in env_file.read_text(
        encoding="utf-8", errors="ignore"
    ):
        print("[확인] 관리자 키 파일이 이미 있습니다.")
        return

    title("3/3 관리자 키 생성")
    admin_key = secrets.token_hex(24)
    existing = ""
    if env_file.exists():
        existing = env_file.read_text(encoding="utf-8", errors="ignore").rstrip()
        if existing:
            existing += "\n"
    env_file.write_text(existing + f"ADMIN_API_KEY={admin_key}\n", encoding="utf-8")
    print(f"관리자 키: {admin_key}")
    print("관리자 페이지에서 필요하므로 따로 보관하세요.")


def open_browser() -> None:
    webbrowser.open(APP_URL)


def start_server() -> int:
    title("PC Auto Builder 서버 시작")
    print(f"브라우저 주소: {APP_URL}")
    print("서버를 끄려면 VS Code 터미널에서 Ctrl+C를 누르세요.\n")
    threading.Timer(2.5, open_browser).start()

    command = [
        str(VENV_PYTHON),
        "-m",
        "uvicorn",
        "app.main:app",
        "--reload",
        "--host",
        "127.0.0.1",
        "--port",
        "8000",
    ]
    completed = subprocess.run(command, cwd=BACKEND_DIR)
    return completed.returncode


def main() -> int:
    try:
        ensure_project_files()
        ensure_venv()
        ensure_packages()
        ensure_env()
        return start_server()
    except KeyboardInterrupt:
        print("\n서버를 종료했습니다.")
        return 0
    except Exception as exc:
        title("실행 중 오류가 발생했습니다")
        print(f"{type(exc).__name__}: {exc}")
        print("\n이 화면을 캡처해서 보내주면 오류 위치를 확인할 수 있습니다.")
        try:
            input("\nEnter를 누르면 종료됩니다...")
        except EOFError:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
