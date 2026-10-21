
from pathlib import Path
from html.parser import HTMLParser
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[5]

RAW = (
    ROOT / "data/raw/usa/employment/west/"
    "2026_second_half/kosaf"
)
BASE = (
    ROOT / "data/processed/usa/employment/west/"
    "2026_second_half"
)

INPUT = BASE / "west_2026_second_half_kosaf_evidence_candidates.json"

OUTPUT = BASE / "west_2026_second_half_kosaf_body_evidence_v2.json"
AUDIT = BASE / "west_2026_second_half_kosaf_body_evidence_audit_v2.json"

INPUT_SHA = (
    "df0cfab9aebf2b8564b1da2e4994ba2"
    "14e65ccdcd5bfe24ab5436dc662ef5030"
)

SOURCE_CONFIG = {
    "kosaf_2026_h2_notice": {
        "filename": "kosaf_2026_h2_notice.html",
        "sha256": (
            "04cb641e65dad90db4e559f5d2f3d688"
            "70b38cb7d1f27e8f4f23df4d9e512d59"
        ),
        "start_anchor": "※ 어학연수비대출은 학자금 지원구간 정보 확인",
        "max_chars": 4000,
    },
    "kosaf_west_loan_guide": {
        "filename": "kosaf_west_loan_guide.html",
        "sha256": (
            "26571e32abaefacab49537568ca054e94"
            "c3ea02173cb71c88f65a75c845ddace"
        ),
        "start_anchor": "단기 WEST 16기(6개월)",
        "max_chars": 4500,
    },
}

# 공식 공지의 검토 질문에 대응하는 근거 단서.
# 단순 출현 확인이며 정책 의미 승인이 아니다.
CHECKS = {
    "WEST-H2-CROSS-01": [
        "학자금 지원구간 정보 확인",
        "어학연수비대출 실행은 추후 합격자 대상으로",
    ],
    "WEST-H2-CROSS-02": [
        "2026. 7. 6.(월) 09:00",
        "8. 5.(수) 17:00",
        "8. 5.(수) 18시",
    ],
    "WEST-H2-CROSS-03": [
        "재학생, 휴학생, 초과학기자, 수료자",
        "졸업생은 한국장학재단 어학연수비 대출신청 제외",
    ],
    "WEST-H2-CROSS-04": [
        "졸업생",
        "학자금 지원구간 통지서",
        "국립국제교육원에 별도 제출",
    ],
    "WEST-H2-CROSS-05": [
        "가구원 정보제공 동의(필수)",
    ],
    "WEST-H2-CROSS-06": [
        "재외국민전형 입학자",
        "국외 소득·재산 신고",
    ],
    "WEST-H2-CROSS-07": [
        "합격자 발표 이전까지 확정된 학자금 지원구간",
    ],
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verified_bytes(path, expected):
    if not path.is_file():
        raise FileNotFoundError(path)
    raw = path.read_bytes()
    if sha(raw) != expected:
        raise ValueError(f"SHA-256 불일치: {path}")
    return raw


class HTMLText(HTMLParser):
    # STEP 64-72와 동일한 텍스트 추출 방식
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip_depth += 1
        elif self.skip_depth == 0 and tag in (
            "p", "div", "tr", "li", "br", "h1", "h2", "h3"
        ):
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self.skip_depth = max(0, self.skip_depth - 1)
        elif self.skip_depth == 0 and tag in (
            "p", "div", "tr", "li"
        ):
            self.parts.append("\n")

    def handle_data(self, data):
        if self.skip_depth == 0:
            self.parts.append(data)


def html_to_text(raw):
    decoded = []
    for encoding in ("utf-8", "cp949", "euc-kr"):
        value = raw.decode(encoding, errors="replace")
        decoded.append((
            value.count("\ufffd"), encoding, value
        ))

    _, encoding, html = min(
        decoded, key=lambda item: item[0]
    )

    parser = HTMLText()
    parser.feed(html)

    text = "".join(parser.parts)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip(), encoding


def compact(text):
    return re.sub(r"\s+", "", text).casefold()


def find_compact_span(text, phrase):
    # 공백을 무시하면서 실제 원문 위치를 복원
    chars = []
    offsets = []

    for index, char in enumerate(text):
        if not char.isspace():
            chars.append(char.casefold())
            offsets.append(index)

    normalized = "".join(chars)
    needle = compact(phrase)

    position = normalized.find(needle)
    if position < 0:
        return None

    end_index = position + len(needle) - 1
    return offsets[position], offsets[end_index] + 1


def save_once(path, obj):
    raw = (
        json.dumps(obj, ensure_ascii=False, indent=2)
        + "\n"
    ).encode("utf-8")

    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(
                f"기존 결과 덮어쓰기 금지: {path}"
            )
        state = "EXISTS_VERIFIED"
    else:
        with path.open("xb") as handle:
            handle.write(raw)
        state = "CREATED"

    return state, sha(raw)


print("===== STEP 64-73 KOSAF 정책 본문 근거 재검수 =====")

# 1. 이전 결과 무결성 검증
candidate = json.loads(
    verified_bytes(INPUT, INPUT_SHA).decode("utf-8")
)

assert candidate["program_id"] == "US-WEST-01"
assert candidate["notice_period"] == "2026_second_half"
assert candidate["approved_for_user_answers"] is False
assert candidate["approved_for_embedding"] is False
assert candidate["automatic_eligibility_rules_enabled"] is False

if len(candidate["candidates"]) != 14:
    raise ValueError("기존 근거 후보 14건 불일치")

print("[PASS] STEP 64-72 SHA-256 및 보호 설정")

# 2. 실제 HTML에서 원문 재추출
sections = {}
source_audits = {}

for source_id, config in SOURCE_CONFIG.items():
    path = RAW / config["filename"]
    raw = verified_bytes(path, config["sha256"])

    text, encoding = html_to_text(raw)

    expected_text_sha = (
        candidate["sources"][source_id]
        ["extracted_text_sha256"]
    )

    if sha(text.encode("utf-8")) != expected_text_sha:
        raise ValueError(
            f"{source_id}: 텍스트 추출 결과가 "
            "STEP 64-72와 일치하지 않음"
        )

    anchor = find_compact_span(
        text, config["start_anchor"]
    )

    if anchor is None:
        raise ValueError(
            f"{source_id}: WEST 본문 시작 지점 미확인"
        )

    start = anchor[0]
    end = min(
        len(text), start + config["max_chars"]
    )
    body = text[start:end]

    sections[source_id] = {
        "full_text": text,
        "start": start,
        "end": end,
        "body": body,
    }

    source_audits[source_id] = {
        "raw_sha256": config["sha256"],
        "extracted_text_sha256": expected_text_sha,
        "encoding": encoding,
        "body_start_offset": start,
        "body_end_offset": end,
        "anchor": config["start_anchor"],
        "section_boundary_manually_verified": False,
        "anchor_is_policy_specific": True,
    }

    print(
        f"[PASS] WEST 본문 후보 분리: {source_id}"
    )

# 3. 7개 교차 검토 항목의 공지 본문 확인
notice = sections["kosaf_2026_h2_notice"]
results = []

for task_id, phrases in CHECKS.items():
    evidence = []

    for phrase in phrases:
        match = find_compact_span(
            notice["body"], phrase
        )

        if match is None:
            evidence.append({
                "searched_phrase": phrase,
                "found_in_notice_body": False,
                "excerpt": None,
                "source_text_offset": None,
            })
            continue

        local_start, local_end = match
        absolute_start = notice["start"] + local_start

        excerpt = notice["body"][
            max(0, local_start - 120):
            min(len(notice["body"]), local_end + 220)
        ].strip()

        evidence.append({
            "searched_phrase": phrase,
            "found_in_notice_body": True,
            "excerpt": excerpt,
            "source_text_offset": absolute_start,
        })

    found = sum(
        item["found_in_notice_body"]
        for item in evidence
    )

    status = (
        "all_body_phrases_found"
        if found == len(phrases)
        else "partial_body_phrases_found"
        if found > 0
        else "no_body_phrases_found"
    )

    results.append({
        "task_id": task_id,
        "source_id": "kosaf_2026_h2_notice",
        "expected_phrase_count": len(phrases),
        "found_phrase_count": found,
        "body_search_status": status,
        "evidence": evidence,
        "section_isolation_reviewed_by_human": False,
        "policy_semantics_approved": False,
        "validation_status": "needs_review",
    })

    print(f"[PASS] {task_id}: {status} ({found}/{len(phrases)})")

# 4. 본문 증거만 별도 저장
result = {
    "dataset_type": "west_kosaf_body_evidence_review",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "historical_notice": True,
    "input_candidate_sha256": INPUT_SHA,
    "sources": source_audits,
    "notice_evidence_results": results,
    "notice_task_count": len(results),
    "website_navigation_matches_excluded_by_body_window": True,
    "cross01_boundary_fix_integrated": True,
    "body_window_end_is_heuristic": True,
    "guide_policy_body_preserved_for_future_comparison": True,
    "source_context_review_completed": False,
    "policy_semantics_approved": False,
    "current_policy_verified": False,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

audit = {
    "dataset_type": "west_kosaf_body_evidence_audit",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "input_sha256": INPUT_SHA,
    "source_count": len(source_audits),
    "cross_agency_tasks": len(results),
    "total_phrase_checks": sum(len(x) for x in CHECKS.values()),
    "body_phrases_found": sum(
        item["found_phrase_count"]
        for item in results
    ),
    "human_semantic_reviews_completed": 0,
    "original_files_modified": False,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

# 실패나 충돌로 결과 파일 한 쪽만 생성되지 않도록 선검사.
for target, obj in ((OUTPUT, result),):
    expected = (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if target.exists() and target.read_bytes() != expected:
        raise FileExistsError(f"기존 결과 충돌: {target}")

state, result_sha = save_once(OUTPUT, result)
audit["result_sha256"] = result_sha
audit_state, audit_sha = save_once(AUDIT, audit)

# 5. 입력 원본 재검증
verified_bytes(INPUT, INPUT_SHA)

for source_id, config in SOURCE_CONFIG.items():
    verified_bytes(
        RAW / config["filename"],
        config["sha256"],
    )

print("\n===== STEP 64-73 최종 결과 =====")
print("보관 원본 검증:", len(source_audits))
print("공지 본문 검토 작업:", len(results))
print(
    "본문 근거 문구 확인:",
    audit["body_phrases_found"],
    "/", audit["total_phrase_checks"]
)

print(f"[PASS] {state}: {OUTPUT.name}")
print("SHA-256:", result_sha)
print(f"[PASS] {audit_state}: {AUDIT.name}")
print("SHA-256:", audit_sha)
print("원본 변경: 없음")
print("정책 의미 최종 승인: 미완료")
print("답변·임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git commit·push: 미실행")