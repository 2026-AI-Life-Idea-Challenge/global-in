# 팀 개발용 데이터 — 2026-10-28

이 묶음은 팀원이 DB 계정 없이 데이터 개발·검색·화면 연동을 시작하기 위한 오프라인 스냅샷이다. 현행 검토 대상 570개는 범위를 명시한 내부 문구 판정을 마쳤고 과거 WEST 공고 20개는 보관본으로 구분했다. 호주462·독일 공제 문구는 원문 근거에 대한 검토자의 해석이며 기관의 새 회신이 아니다. 독립 법률의견서나 운영 서비스 개방본으로 해석하지 않는다. 상세 상태는 `review_status.json`에서 확인한다.

## 시작

ZIP을 빈 폴더에 풀고 Python 3.10 이상에서 실행한다. 별도 라이브러리는 필요 없다.

```shell
python verify_bundle.py
```

검증 성공 후 SQLite 도구로 `global_in_review.sqlite`를 연다. 새 검토 문구는 아래 테이블에서 읽는다.

```sql
SELECT policy_id, country, policy_text, review_scope, version
FROM reviewed_policies
ORDER BY country, policy_id;
```

- `reviewed_policies`: 승인 범위가 명시된 새 문구. 개인 자격 판정·사용자 답변·임베딩 자동 사용 허용은 0이다.
- `policy_dispositions`: 전체 590개 판정. 과거 공고와 미승인도 포함한다.
- `policy_candidates`, `programs`, `evidence`, `support_programs`: 원본 DB 행을 `row_json`에 보존한다. 원본 본문과 새 검토 문구를 혼용하지 않는다.
- `db_snapshot.json`: PostgreSQL 자료형을 JSON으로 직렬화한 네 테이블 전체. 비밀번호·계정·환경설정·임베딩은 포함하지 않는다.
- `policy_registry.json`: 승인 문구·범위·출처·해시·재검토 조건.
- `evidence_files/`: 승인 근거 파일을 기존 상대 경로로 보존했다. 웹 도구/브라우저 전사 기록은 서버 원본 파일과 구분한다.
- `manifest.json`: 모든 파일의 SHA256과 건수. 수정 후에는 원본 묶음 검증을 통과하지 않는다.

원문 URL은 `db_snapshot.json`의 evidence 테이블에 있으며 각 정책의 `source_evidence_ids`로 연결한다. 추가 검토 출처는 `policy_registry.json`의 `source_references`에 있다.

개발·분석·내부 검토에 사용한다. 미승인 및 과거 공고를 현행 확정 요건으로 사용하거나 0인 서비스 플래그를 승인으로 해석하지 않는다. 소송·법령·기관 안내가 바뀌면 해당 문구 버전을 다시 검토한다.
