# 적용된 주요 수정

- 신규/예제 11개 DB를 `exported_parts.json` 100개 시드로 정상 복원
- SQLite WAL, busy timeout, 중복 상품 유니크 인덱스와 `source_url` 컬럼 마이그레이션
- 무GPU 구성은 내장그래픽 CPU만 허용
- 별도 쿨러 미선택 구성은 기본 쿨러 포함 CPU만 허용
- `verified` 과장 표기를 기본 규격 검사로 변경
- 3D 화면에 최신 추천 결과 전달, `model_name` 표시, GPU 길이 강제 축소 제거
- 웹 수집 내부/사설 IP 차단, 리다이렉트 재검사, 응답 2MB 제한
- 대량 수집을 단일 작업 큐로 실행하고 브라우저에서 상태 폴링
- 소스 URL/제품명 중복 검색을 DB 인덱스로 변경
- `.env`가 운영 환경변수를 덮어쓰지 않도록 수정
- `backend/self_test.py` 추가

## 실행

```powershell
.\RUN_FIXED.ps1
```

브라우저: `http://127.0.0.1:8000/app`
