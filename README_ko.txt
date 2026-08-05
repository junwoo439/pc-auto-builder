PC Auto Builder 공개 배포 준비 패키지
====================================

이 패키지는 다음 작업을 자동으로 수행합니다.

1. SQLite 경로를 PC_PARTS_DB_PATH 환경변수로 설정할 수 있게 수정
2. Dockerfile 생성
3. Railway 설정 파일 railway.json 생성
4. .dockerignore 생성
5. 비밀키, 가상환경, 로컬 DB가 GitHub에 올라가지 않도록 .gitignore 보강
6. requirements.txt에 uvicorn이 없으면 추가

설치
----

압축 내용을 다음 폴더에 풉니다.

C:\Users\USER\Documents\GitHub\pc-auto-builder

PowerShell:

cd C:\Users\USER\Documents\GitHub\pc-auto-builder

.\backend\.venv\Scripts\python.exe `
  .\install_public_deployment.py

Railway에서 필요한 설정
------------------------

Volume Mount Path:
  /data

Variables:
  PC_PARTS_DB_PATH=/data/pc_parts.db

관리자 키 환경변수는 현재 프로젝트의 parts.py에서 사용하는 이름과
같은 이름으로 Railway Variables에 등록해야 합니다.

확인 명령:

Select-String `
  .\backend\app\routers\parts.py `
  -Pattern "getenv|environ|ADMIN|KEY" `
  -Context 2,2
