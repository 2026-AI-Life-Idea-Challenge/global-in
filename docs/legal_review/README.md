# 법률 검토 작업 안내

최신 상태는 [진행률](progress_20261028.json)과 [교정·재추출 보고서](us_jp_resolution_20261028.md)에서 확인한다. 상세 범위 기록은 327개 전체에 있고, 검토용 교정본 26개·재추출본 6개가 작성됐다. 최종 법률 승인과 DB 반영은 별도다.

| 분류 | 경로 |
|---|---|
| 공식 원문 수집 | `scripts/crawl/common/` |
| 공통 검토·교정·결과 생성 | `scripts/ingest/common/legal_review/` |
| 국가별 검토 주석 반영 | `scripts/ingest/australia/`, `scripts/ingest/canada/` |
| 일본 아카이브 추적 | `scripts/ingest/japan/trace_japan_source_archives.py` |
| 미국 정책별 검토 문장 | `scripts/ingest/usa/shared/review/us_policy_scope_notes.py` |
| 스냅샷·근거·DB URL 검증 | `scripts/evaluate/legal_review/` |
| 원본 입력 스냅샷 | `data/processed/legal_review/inputs/` |
| 가공 검토 원장·수정본 | `data/processed/legal_review/` |
| 보고서·진행률 | `docs/legal_review/` |

실행 순서는 `scripts/ingest/common/legal_review/README.md`에 정리했다. 경로 이동 이력은 [이동 manifest](file_layout_migration_20261028.json)에 있다. 기존 국가·프로그램별 원문과 가공 데이터의 위치·내용은 유지했다.

협업 시 `data/raw/`는 Git 제외 대상임에 유의한다. 공유용 URL·해시 목록은 `data/processed/legal_review/source_manifest_20261028.json`에 있으며 실제 원문은 이 목록과 일치하는 보관본을 준비해야 한다. `.env`와 DB 자격 증명은 공유하지 않는다.
