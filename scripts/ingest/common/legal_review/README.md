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
# 590개 정책 문구 일괄 판정 재현

최신 문구 판정은 `finalize_global_policy_wording.py`로 재현한다. 고정 입력 해시·정책별 실질 검토·국가별 대체 문구를 사용하며, 임의의 새 데이터에 대한 자동 승인기가 아니다. 원본 DB·원문 스냅샷·서비스 사용 플래그는 변경하지 않는다.

```powershell
.venv\Scripts\python.exe scripts/ingest/australia/finalize_age_policy_review.py
.venv\Scripts\python.exe scripts/ingest/common/legal_review/finalize_global_policy_wording.py
.venv\Scripts\python.exe scripts/ingest/common/legal_review/finalize_global_policy_wording.py --check
.venv\Scripts\python.exe scripts/evaluate/legal_review/audit_policy_content_approvals.py
```

연령 생성기의 결과는 별도 파일에 보존하여 전체 원장의 승인 건수가 6개로 돌아가지 않도록 한다. 최신 원장: `data/processed/legal_review/policy_content_approval_registry_20261028.json`. 보류·다음 조치: `data/processed/legal_review/global_policy_wording_decisions_20261028.json`.

## 팀 개발용 내보내기

`apply_policy_review_metadata.py`는 읽기 전용 미리보기이며 `--apply`일 때만 백업 후 별도 검토 버전을 DB에 저장한다. 원본 본문과 서비스 플래그는 보존한다. 이어서 `export_team_review_bundle.py`를 실행하면 `data/exports/team_review_20261028.zip`에 SQLite·JSON·승인 근거 파일·표준 라이브러리 검증기를 묶는다. ZIP 자체를 다시 풀어 독립 검증한 뒤에만 최종 파일로 교체한다.

```powershell
.venv\Scripts\python.exe scripts/ingest/common/legal_review/apply_policy_review_metadata.py
.venv\Scripts\python.exe scripts/ingest/common/legal_review/apply_policy_review_metadata.py --apply
.venv\Scripts\python.exe scripts/ingest/common/legal_review/export_team_review_bundle.py
```

DB 연결은 `.env`를 사용하지만 자격증명은 출력·내보내기하지 않는다. 팀원이 받은 ZIP을 풀고 `python verify_bundle.py`를 실행하면 별도 설치나 DB 계정 없이 검증한다. 미승인과 승인 범위 밖 쟁점을 `review_status.json`에 포함하므로 개발 준비 완료와 전체 법률 검토 완료를 혼동하지 않는다.
