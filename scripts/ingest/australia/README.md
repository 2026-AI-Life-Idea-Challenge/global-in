# 호주 자료 대조 및 법령 범위 기록

공개 자료 후속 검토와 범위를 명시한 문구 검증은 다음 순서다. 입력·출처가 바뀌면 근거를 재검토한 후 실행한다.

```powershell
pwsh -NoProfile -File scripts/crawl/common/collect_australia_statutory_sources.ps1 -FollowupOnly
.venv\Scripts\python.exe scripts/ingest/australia/build_public_followup.py
.venv\Scripts\python.exe scripts/evaluate/legal_review/audit_australia_public_followup.py
.venv\Scripts\python.exe scripts/ingest/australia/finalize_age_policy_review.py
.venv\Scripts\python.exe scripts/ingest/australia/finalize_age_policy_review.py --check
.venv\Scripts\python.exe scripts/evaluate/legal_review/audit_policy_content_approvals.py
```

`finalize_age_policy_review.py`는 실질 대조한 여섯 연령 문구 버전만 기록한다. 다른 정책이나 개인의 자격을 자동 승인하지 않고 DB에도 쓰지 않는다. 일반 문구 검증을 변호사 서명이나 서비스 사용 승인과 구분한다. 진행률을 쓰는 생성기는 순차 실행한다.

프로젝트 루트에서 실행한다.

```powershell
# 공식 법령 본문 수집. 캐시 재사용; 재수집하려면 -Refresh 추가.
pwsh -NoProfile -File scripts/crawl/common/collect_australia_statutory_sources.ps1

# 원본 정책을 바꾸지 않고 별도 검토 원장·근거 보완본 생성
.venv\Scripts\python.exe scripts/ingest/australia/build_statutory_scope_review.py

# 재현성 및 별도 무결성 검사
.venv\Scripts\python.exe scripts/ingest/australia/build_statutory_scope_review.py --check
.venv\Scripts\python.exe scripts/evaluate/legal_review/audit_australia_statutory_review.py
```

`apply_australia_official_review.py --check`는 기존 공식 안내 페이지 대조 주석을 검사한다. 법령 범위 기록과 다른 단계다.

입력 스냅샷은 `data/processed/legal_review/inputs/`, 법령 원문과 189 화면 본문 보관은 `data/raw/legal_review/20261028/australia/`, 결과는 `data/processed/legal_review/australia_*20261028.json`, 설명은 `docs/legal_review/australia_statutory_scope_20261028.md`에 있다.

189의 네 세부 본문은 실제 공식 화면에서 펼친 DOM을 정규화해 별도로 저장했다. 수집 PS1만으로 이 화면 캡처가 재현되지는 않는다. 새로 확보하려면 공식 Eligibility 화면에서 네 항목을 펼쳐 관찰하고 캡처 파일을 갱신해야 한다. 보완 Evidence는 기존 ID를 덮어쓰지 않으며 DB에는 아직 삽입하지 않는다.

원문은 Git 제외 대상이다. 협업자는 공유 manifest의 URL·해시·파일 경로와 일치하는 원문과 189 캡처 파일을 준비해야 한다. 단순 재수집으로 같은 해시가 보장되지는 않는다. 생성기는 실제 파일 해시와 manifest를 대조하고 누락되거나 목록 화면만 저장된 경우 실패한다.

법령 조문 경로는 명시적 매핑이며, 정책별 검토 메모는 공통 검토 규칙을 조합한다. 최종 승인·DB 쓰기·임베딩 실행 기능은 없다. 독일 생성기를 재실행해도 호주의 후속 진행 기록을 보존한다.
