다나와 상세 규격 자동 갱신 패키지

설치:
1. ZIP을 pc-auto-builder 프로젝트 최상위 폴더에 압축 해제합니다.
2. 프로젝트 최상위 폴더에서 실행:
   backend\.venv\Scripts\python.exe .\install_spec_updates.py
3. 검사:
   cd backend
   .\.venv\Scripts\python.exe -m compileall .\app
   .\.venv\Scripts\python.exe -c "from app.main import app; print('/spec-updates/all' in app.openapi()['paths'])"
4. 서버:
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
5. http://127.0.0.1:8000/admin 접속
   - 체크 후 '선택 부품 상세 규격 갱신'
   - 또는 '전체 부품 상세 규격 갱신'

동작:
- 다나와 source_url을 방문해 상세 스펙을 분석합니다.
- CPU 소켓, 메인보드 RAM/폼팩터, GPU 길이/권장 파워,
  케이스 치수, 파워 용량, 쿨러 소켓, RAM 규격, 저장장치 규격을 저장합니다.
- 잘못 psu로 분류된 다나와 수랭쿨러도 cate 값을 기준으로 cooler로 고칩니다.
- 완료 후 backend/app/data/exported_parts.json도 자동 갱신합니다.
