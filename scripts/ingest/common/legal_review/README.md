# 국가 공통 법률 검토

미국·일본 통합 검토와 여러 국가의 인용 교정 코드를 관리한다. 국가별 반영 도구는 `scripts/ingest/australia/`, `scripts/ingest/canada/`, 일본 아카이브 추적은 `scripts/ingest/japan/`에 있다. 미국 정책별 검토 문장은 `scripts/ingest/usa/shared/review/us_policy_scope_notes.py`에서 관리한다.

프로젝트 루트에서 다음 순서로 실행한다.

```powershell
.venv\Scripts\python.exe scripts/ingest/common/legal_review/build_remaining_us_jp_scope.py
.venv\Scripts\python.exe scripts/ingest/common/legal_review/audit_us_jp_official_review.py
.venv\Scripts\python.exe scripts/ingest/common/legal_review/summarize_us_jp_scope.py
.venv\Scripts\python.exe scripts/ingest/common/legal_review/resolve_us_jp_review.py
```

인용 교정본을 다시 생성할 때:

```powershell
.venv\Scripts\python.exe scripts/ingest/common/legal_review/repair_evidence_quotes.py
```

- 입력: `data/processed/legal_review/inputs/global_in_policy_audit_input_20261027.json`
- 가공 검토본: `data/processed/legal_review/`
- 보고서·진행률: `docs/legal_review/`
- 원문 수집: `scripts/crawl/common/collect_us_jp_review_sources.ps1`
- 검증: `scripts/evaluate/legal_review/`

실행은 확보한 원문 및 기록된 관찰을 재현한다. DB에 쓰거나 최종 법률·자격 판정 승인을 부여하지 않는다. 원문 파일은 `data/raw/`에 있어 Git에서 제외된다. 공유에 필요한 URL·해시·파일 위치는 `data/processed/legal_review/source_manifest_20261028.json`에서 확인한다.
