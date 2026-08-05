# PC 부품 대량 수집 제한 확장

## 변경 내용

- 최대 목록 페이지: 50 → 100
- 최대 상품 수: 300 → 1,000
- 기본 목록 페이지: 10 → 20
- 기본 상품 수: 100 → 500
- 화면 입력 범위 안내 및 정수 검증 추가
- 수집 중 버튼 중복 클릭 방지는 기존 기능 유지

## 설치

압축 내용을 `pc-auto-builder` 프로젝트 최상위에 풀고 다음 명령을 실행합니다.

```powershell
.\backend\.venv\Scripts\python.exe .\install_bulk_import_limits.py
```

서버를 다시 시작합니다.

```powershell
cd .\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

대량 수집 화면:

```text
http://127.0.0.1:8000/bulk-import
```

## 주의

이 패치는 요청 한도만 확장합니다. 수집 작업은 현재 구조처럼 하나의 HTTP 요청에서 동기적으로 실행됩니다. 상품별 대기 시간이 1초라면 1,000개는 네트워크 지연을 제외해도 약 17분 이상 걸릴 수 있습니다. 수집 중에는 서버와 브라우저를 닫지 마세요.
