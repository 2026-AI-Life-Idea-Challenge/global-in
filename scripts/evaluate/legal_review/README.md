# 법률 검토 데이터 검증

프로젝트 루트에서 실행한다.

```powershell
.venv\Scripts\python.exe scripts/evaluate/legal_review/audit_policy_snapshot.py
.venv\Scripts\python.exe scripts/evaluate/legal_review/audit_evidence_followup.py
```

`audit_db_source_urls.py`는 `.env`의 DB에 연결해 읽기 전용 트랜잭션으로 URL 연결 상태를 검사한다. 로컬 파일 검사에는 DB 접속이 필요하지 않다.

```powershell
.venv\Scripts\python.exe scripts/evaluate/legal_review/audit_db_source_urls.py
```

국가별 주석 검사는 다음 경로를 사용한다.

```powershell
.venv\Scripts\python.exe scripts/ingest/australia/apply_australia_official_review.py --check
.venv\Scripts\python.exe scripts/ingest/canada/apply_canada_official_review.py --check
```

입력 스냅샷은 `data/processed/legal_review/inputs/`, 결과는 `docs/legal_review/`에 저장한다. 검증 성공은 법률 검증 최종 승인을 뜻하지 않는다.
