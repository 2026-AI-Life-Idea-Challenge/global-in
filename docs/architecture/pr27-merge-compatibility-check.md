# PR #27 병합 호환성 추가 확인

기준: `develop`의 PR #26 병합 커밋 `29701b9`, MJfront 호환 병합 `bed61fc`.

## 팀원 파일 보존

다음 파일은 `git diff origin/develop -- <파일>`로 차이가 없음을 확인했다.

- `app/agent/preparation_planning.py`
- `app/services/b_question_router.py`
- `app/services/recommendation_context.py`
- `app/services/multi_program_rag.py`
- `scripts/b_cases.py`
- `scripts/evaluate_support_rag.py`

`user_understanding.py`의 충돌은 팀원의 answer_mode 분류·혼합 질문 확인 요청과 MJfront의 프로필 필드 확장·워홀 개요 범위를 함께 반환하도록 해결했다. `official_information.py`의 팀원 RAG 검증 실패 처리와 `rag_llm.py`의 PURPOSE_ANSWER_RULES도 유지한다.

## 추가 실행 검사

`tests/unit/test_consult_flow.py`에 4개 검사를 추가했다. 컴파일된 전체 그래프와 FastAPI 상담 세션 API를 사용하며, 외부 DB·LLM 입출력은 합성 응답으로 고정해 병합 호환성을 검사한다.

1. general: 준비 안내로 이동하고 RAG 생성은 호출하지 않는다.
2. evidence: RAG·출처를 반환하고 일반 준비 안내를 추가 호출하지 않는다.
3. mixed: 근거 답변과 일반 준비 안내를 함께 반환한다.
4. mixed + 개인 정보 부족: 필요한 국적·생년월일 확인 요청을 보존하고 RAG를 임의 실행하지 않는다.

첫 3개 검사에서는 확장 프로필 필드와 answer_mode가 동일 추출 스키마에 있고, 다음 턴에도 국적·전공이 보존되는지 확인한다.

추가 후 전체 Python 테스트 280개 + 223 subtests 통과(기존 경고 4개). 이 결과는 외부 모델의 모든 의도 분류나 답변 의미를 보장하는 검사가 아니라, 두 작업의 라우팅·프로필·응답 결합이 함께 작동하는 회귀 검사다.
