from __future__ import annotations

import py_compile
import re
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATABASE_FILE = ROOT / "backend" / "app" / "data" / "database.py"
REQUIREMENTS_FILE = ROOT / "backend" / "requirements.txt"
DOCKERFILE = ROOT / "Dockerfile"
RAILWAY_FILE = ROOT / "railway.json"
DOCKERIGNORE_FILE = ROOT / ".dockerignore"
GITIGNORE_FILE = ROOT / ".gitignore"


def backup(path: Path) -> None:
    if not path.exists():
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = path.with_name(f"{path.name}.before_public_deploy_{stamp}")
    shutil.copy2(path, target)
    print(f"백업: {target.relative_to(ROOT)}")


def patch_database() -> None:
    if not DATABASE_FILE.exists():
        raise FileNotFoundError(
            f"데이터베이스 파일을 찾지 못했습니다: {DATABASE_FILE}"
        )

    backup(DATABASE_FILE)
    content = DATABASE_FILE.read_text(encoding="utf-8-sig")

    if "import os\n" not in content:
        if "import json\n" in content:
            content = content.replace(
                "import json\n",
                "import json\nimport os\n",
                1,
            )
        else:
            content = "import os\n" + content

    replacement = '''_DEFAULT_DATABASE_PATH = (
    Path(__file__).resolve().parents[2]
    / "pc_parts.db"
)

DATABASE_PATH = Path(
    os.getenv(
        "PC_PARTS_DB_PATH",
        str(_DEFAULT_DATABASE_PATH),
    )
).expanduser()

DATABASE_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)
'''

    pattern = re.compile(
        r"DATABASE_PATH\s*=\s*\(\s*"
        r"Path\(__file__\)\.resolve\(\)\.parents\[2\]\s*"
        r"/\s*[\"']pc_parts\.db[\"']\s*"
        r"\)\s*",
        re.MULTILINE,
    )

    if "PC_PARTS_DB_PATH" not in content:
        content, count = pattern.subn(
            replacement + "\n",
            content,
            count=1,
        )
        if count != 1:
            raise RuntimeError(
                "database.py의 DATABASE_PATH 부분을 자동으로 찾지 못했습니다."
            )
        print("수정: PC_PARTS_DB_PATH 환경변수 지원")
    else:
        print("건너뜀: PC_PARTS_DB_PATH가 이미 적용되어 있습니다.")

    DATABASE_FILE.write_text(content, encoding="utf-8")
    py_compile.compile(
        str(DATABASE_FILE),
        doraise=True,
    )
    print("검사: database.py 문법 정상")


def ensure_requirements() -> None:
    if not REQUIREMENTS_FILE.exists():
        raise FileNotFoundError(
            f"requirements.txt를 찾지 못했습니다: {REQUIREMENTS_FILE}"
        )

    content = REQUIREMENTS_FILE.read_text(
        encoding="utf-8-sig"
    )
    lines = [
        line.strip().lower()
        for line in content.splitlines()
        if line.strip()
    ]

    if not any(
        line.startswith("uvicorn")
        for line in lines
    ):
        with REQUIREMENTS_FILE.open(
            "a",
            encoding="utf-8",
        ) as file:
            if content and not content.endswith("\n"):
                file.write("\n")
            file.write("uvicorn[standard]\n")
        print("추가: uvicorn[standard]")
    else:
        print("확인: uvicorn 요구사항 존재")


def write_deployment_files() -> None:
    dockerfile = '''FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt

RUN python -m pip install --no-cache-dir --upgrade pip \\
    && python -m pip install --no-cache-dir \\
       -r /app/backend/requirements.txt

COPY backend /app/backend
COPY frontend /app/frontend

WORKDIR /app/backend

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
'''

    railway = '''{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "healthcheckPath": "/health",
    "healthcheckTimeout": 120,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
'''

    dockerignore = '''.git
.github
**/.venv
**/__pycache__
**/*.pyc
.env
backend/.env
backend/pc_parts.db
*.db
*.sqlite
*.sqlite3
*.zip
*.before_*
*.before_public_deploy_*
'''

    for path, content in (
        (DOCKERFILE, dockerfile),
        (RAILWAY_FILE, railway),
        (DOCKERIGNORE_FILE, dockerignore),
    ):
        if path.exists():
            backup(path)
        path.write_text(content, encoding="utf-8")
        print(f"생성: {path.relative_to(ROOT)}")


def update_gitignore() -> None:
    block = '''
# Public deployment
.env
backend/.env
backend/.venv/
**/__pycache__/
**/*.pyc
backend/pc_parts.db
*.sqlite
*.sqlite3
*.zip
*.before_*
'''
    current = ""
    if GITIGNORE_FILE.exists():
        current = GITIGNORE_FILE.read_text(
            encoding="utf-8-sig"
        )

    if "# Public deployment" not in current:
        if current and not current.endswith("\n"):
            current += "\n"
        current += block.lstrip("\n")
        GITIGNORE_FILE.write_text(
            current,
            encoding="utf-8",
        )
        print("수정: .gitignore")
    else:
        print("건너뜀: .gitignore 배포 항목이 이미 있습니다.")


def main() -> None:
    patch_database()
    ensure_requirements()
    write_deployment_files()
    update_gitignore()

    print()
    print("공개 배포 준비 완료")
    print()
    print("다음 명령:")
    print("  git status")
    print("  git add .")
    print('  git commit -m "Prepare Railway public deployment"')
    print("  git push")


if __name__ == "__main__":
    main()
