
from pathlib import Path
from html.parser import HTMLParser
from collections import Counter
import hashlib
import json
import re


# ============================================================
# STEP 64-72
# 한국장학재단 보관 HTML에서 WEST 정책 근거 후보 추출
#
# 원본 변경 없음
# 외부 네트워크 요청 없음
# 자동 의미 검수/승인/임베딩 없음
# ============================================================

ROOT = Path(__file__).resolve().parents[5]

RAW_DIR = (
    ROOT
    / "data/raw/usa/employment/west/2026_second_half/kosaf"
)

BASE = (
    ROOT
    / "data/processed/usa/employment/west/2026_second_half"
)

MANIFEST = RAW_DIR / "kosaf_source_manifest.json"

COMPARISON = (
    BASE / "west_2026_second_half_cross_agency_comparison.json"
)

OUTPUT = (
    BASE / "west_2026_second_half_kosaf_evidence_candidates.json"
)

AUDIT = (
    BASE / "west_2026_second_half_kosaf_evidence_audit.json"
)

EXPECTED_MANIFEST_SHA = (
    "001e251516619a4d60cc6dd2569e165"
    "bb4b445c3244228862ad8cf4ef32f2600"
)

EXPECTED_COMPARISON_SHA = (
    "8ed7ff07eb016e8277d90a203f80b935"
    "c1fe201ea00c429d7571cea444c7b1f6"
)

EXPECTED_HTML_SHA = {
    "kosaf_2026_h2_notice": (
        "04cb641e65dad90db4e559f5d2f3d688"
        "70b38cb7d1f27e8f4f23df4d9e512d59"
    ),
    "kosaf_west_loan_guide": (
        "26571e32abaefacab49537568ca054e94"
        "c3ea02173cb71c88f65a75c845ddace"
    ),
}

# 검증할 문구를 검색어 그룹으로 나눈다.
# 여러 검색어가 발견되어도 정책 의미를 승인하지 않는다.
SEARCH_GROUPS = {
    "WEST-H2-CROSS-01": [
        ["지원구간", "학자금 지원구간"],
        ["대출신청", "대출 신청"],
        ["대출실행", "대출 실행"],
    ],
    "WEST-H2-CROSS-02": [
        ["7월 6일", "7.6.", "07.06"],
        ["8월 5일", "8.5.", "08.05"],
        ["17시", "17:00"],
        ["18시", "18:00"],
    ],
    "WEST-H2-CROSS-03": [
        ["재학생"],
        ["휴학생"],
        ["초과학기", "초과 학기"],
        ["수료자"],
        ["졸업생"],
    ],
    "WEST-H2-CROSS-04": [
        ["졸업생"],
        ["지원구간 통지서", "학자금 지원구간 통지서"],
        ["증빙", "제출"],
    ],
    "WEST-H2-CROSS-05": [
        ["가구원"],
        ["정보제공 동의", "정보 제공 동의"],
    ],
    "WEST-H2-CROSS-06": [
        ["재외국민"],
        ["국외 소득", "국외소득"],
        ["재산", "신고"],
    ],
    "WEST-H2-CROSS-07": [
        ["합격자 발표", "최종합격"],
        ["지원구간", "지원 구간"],
        ["최신화", "확정"],
    ],
}

MAX_MATCHES_PER_GROUP_SOURCE = 5
CONTEXT_CHARS = 180


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def require_sha(path, expected):
    if not path.is_file():
        raise FileNotFoundError(path)

    raw = path.read_bytes()
    actual = sha256(raw)

    if actual != expected:
        raise ValueError(
            f"SHA-256 불일치: {path}\n"
            f"예상: {expected}\n실제: {actual}"
        )
    return raw


class HTMLText(HTMLParser):
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
    # 수집 응답이 UTF-8 또는 EUC-KR 계열일 수 있으므로
    # 대체 문자 개수를 비교하여 디코딩 후보를 선택한다.
    decoded = []

    for encoding in ("utf-8", "cp949", "euc-kr"):
        text = raw.decode(encoding, errors="replace")
        decoded.append((
            text.count("\ufffd"),
            encoding,
            text,
        ))

    _, encoding, html = min(decoded, key=lambda x: x[0])

    parser = HTMLText()
    parser.feed(html)

    text = "".join(parser.parts)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip(), encoding


def compact(value):
    return re.sub(r"\s+", "", str(value)).casefold()


def evidence_matches(text, variants, limit):
    # 줄바꿈으로 끊어진 문구도 찾을 수 있도록
    # 공백 제거 문자열에서 검색하고 원문 위치로 역매핑한다.
    chars = []
    positions = []

    for i, ch in enumerate(text):
        if not ch.isspace():
            chars.append(ch.casefold())
            positions.append(i)

    normalized = "".join(chars)
    findings = []
    seen = set()

    for variant in variants:
        needle = compact(variant)
        start = 0

        while len(findings) < limit:
            index = normalized.find(needle, start)

            if index < 0:
                break

            original_start = positions[index]
            original_end = positions[
                index + len(needle) - 1
            ] + 1

            if original_start not in seen:
                seen.add(original_start)

                excerpt = text[
                    max(0, original_start - CONTEXT_CHARS):
                    min(len(text), original_end + CONTEXT_CHARS)
                ]

                findings.append({
                    "matched_variant": variant,
                    "text_start_offset": original_start,
                    "text_end_offset": original_end,
                    "excerpt": excerpt.strip(),
                })

            start = index + len(needle)

        if len(findings) >= limit:
            break

    return sorted(
        findings,
        key=lambda item: item["text_start_offset"]
    )


def encode(data):
    return (
        json.dumps(
            data, ensure_ascii=False, indent=2
        ) + "\n"
    ).encode("utf-8")


def save_once(path, raw):
    if path.exists():
        if path.read_bytes() != raw:
            raise FileExistsError(
                f"기존 출력 파일과 충돌: {path}"
            )
        state = "EXISTS_VERIFIED"
    else:
        with path.open("xb") as f:
            f.write(raw)
        state = "CREATED"

    return state, sha256(raw)


print("===== STEP 64-72 KOSAF 공식 원문 근거 추출 =====")

# 1. 이전 파일 SHA-256 검사
manifest_raw = require_sha(
    MANIFEST, EXPECTED_MANIFEST_SHA
)
comparison_raw = require_sha(
    COMPARISON, EXPECTED_COMPARISON_SHA
)

manifest = json.loads(manifest_raw.decode("utf-8"))
comparison = json.loads(comparison_raw.decode("utf-8"))

for obj in (manifest, comparison):
    if obj["program_id"] != "US-WEST-01":
        raise ValueError("프로그램 ID 불일치")
    if obj["notice_period"] != "2026_second_half":
        raise ValueError("모집 회차 불일치")

    for flag in (
        "approved_for_user_answers",
        "approved_for_embedding",
        "automatic_eligibility_rules_enabled",
    ):
        if obj.get(flag) is not False:
            raise ValueError(f"보호 설정 오류: {flag}")

print("[PASS] 매니페스트 및 STEP 64-68 SHA-256")

# 2. 보관 원문 2개의 SHA-256 검증
source_texts = {}
source_metadata = {}

records = manifest["sources"]

if len(records) != 2:
    raise ValueError("보관 원문 수 2개 불일치")

for record in records:
    source_id = record["source_id"]

    if source_id not in EXPECTED_HTML_SHA:
        raise ValueError(
            f"허용되지 않은 출처 ID: {source_id}"
        )

    expected = EXPECTED_HTML_SHA[source_id]

    if record["sha256"] != expected:
        raise ValueError(
            f"{source_id}: 매니페스트 SHA-256 불일치"
        )

    filename = record["filename"]

    # 파일 이름 조작으로 RAW_DIR 밖을 읽지 않도록 제한
    if Path(filename).name != filename:
        raise ValueError("잘못된 원본 파일 이름")

    raw = require_sha(RAW_DIR / filename, expected)

    if len(raw) != record["size_bytes"]:
        raise ValueError(
            f"{source_id}: 파일 크기 불일치"
        )

    text, encoding = html_to_text(raw)

    if len(text) < 300:
        raise ValueError(
            f"{source_id}: 추출된 HTML 텍스트 부족"
        )

    if compact("WEST") not in compact(text):
        raise ValueError(
            f"{source_id}: WEST 문맥 확인 실패"
        )

    source_texts[source_id] = text

    source_metadata[source_id] = {
        "filename": filename,
        "source_url": record["final_url"],
        "raw_sha256": expected,
        "raw_size_bytes": len(raw),
        "decoded_encoding": encoding,
        "extracted_text_sha256": sha256(
            text.encode("utf-8")
        ),
        "extracted_text_length": len(text),
        "page_scope_isolated": False,
    }

    print(
        f"[PASS] 보관 HTML 무결성: {source_id}"
    )

# 3. STEP 64-68 검토 항목과 원문 문구 연결
task_ids = {
    item["task_id"]
    for item in comparison["results"]
}

if task_ids != set(SEARCH_GROUPS):
    raise ValueError("교차 검토 항목 ID 불일치")

candidates = []
status_counts = Counter()

for task_id, groups in SEARCH_GROUPS.items():
    for source_id, text in source_texts.items():
        group_results = []

        for group_index, variants in enumerate(groups, 1):
            matches = evidence_matches(
                text,
                variants,
                MAX_MATCHES_PER_GROUP_SOURCE,
            )

            group_results.append({
                "group_number": group_index,
                "searched_variants": variants,
                "matched": bool(matches),
                "matches": matches,
            })

        found_groups = sum(
            item["matched"] for item in group_results
        )

        status = (
            "all_search_groups_found"
            if found_groups == len(groups)
            else "partial_search_groups_found"
            if found_groups > 0
            else "no_search_groups_found"
        )

        status_counts[status] += 1

        candidates.append({
            "task_id": task_id,
            "source_id": source_id,
            "search_group_count": len(groups),
            "matched_search_groups": found_groups,
            "search_status": status,
            "evidence_groups": group_results,
            "policy_claim_verified": False,
            "review_status": "evidence_candidate",
            "manual_context_review_required": True,
        })

    print(f"[PASS] {task_id}: 검색 후보 생성")


# 4. 출력
result = {
    "dataset_type": "west_kosaf_evidence_candidates",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "historical_notice": True,
    "manifest_sha256": EXPECTED_MANIFEST_SHA,
    "cross_agency_comparison_sha256": (
        EXPECTED_COMPARISON_SHA
    ),
    "sources": source_metadata,
    "candidate_count": len(candidates),
    "candidates": candidates,
    "search_status_counts": dict(status_counts),
    "source_pages_section_isolated": False,
    "policy_claims_independently_verified": False,
    "external_source_snapshots_sha256_verified": True,
    "semantic_review_completed": False,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

audit = {
    "dataset_type": "west_kosaf_evidence_audit",
    "program_id": "US-WEST-01",
    "notice_period": "2026_second_half",
    "source_count": len(source_metadata),
    "cross_agency_task_count": len(SEARCH_GROUPS),
    "task_source_candidate_count": len(candidates),
    "search_status_counts": dict(status_counts),
    "policy_claims_verified": 0,
    "human_semantic_review_completed": False,
    "raw_source_files_modified": False,
    "validation_status": "needs_review",
    "approved_for_user_answers": False,
    "approved_for_embedding": False,
    "automatic_eligibility_rules_enabled": False,
}

result_raw = encode(result)
result_sha = sha256(result_raw)

audit["result_sha256"] = result_sha
audit_raw = encode(audit)

# 두 출력 파일 모두 충돌을 먼저 확인
for path, raw in (
    (OUTPUT, result_raw),
    (AUDIT, audit_raw),
):
    if path.exists() and path.read_bytes() != raw:
        raise FileExistsError(
            f"기존 출력 내용과 불일치: {path}"
        )

state, result_sha = save_once(OUTPUT, result_raw)
audit_state, audit_sha = save_once(AUDIT, audit_raw)

# 5. 최종 입력 무결성 재확인
require_sha(MANIFEST, EXPECTED_MANIFEST_SHA)
require_sha(COMPARISON, EXPECTED_COMPARISON_SHA)

for source_id, meta in source_metadata.items():
    require_sha(
        RAW_DIR / meta["filename"],
        meta["raw_sha256"],
    )

print("\n===== STEP 64-72 최종 결과 =====")
print("검증된 HTML 원본:", len(source_metadata))
print("교차 검토 작업:", len(SEARCH_GROUPS))
print("출처별 근거 검색 결과:", len(candidates))

for status, count in sorted(status_counts.items()):
    print(f"{status}: {count}")

print(f"[PASS] {state}: {OUTPUT.name}")
print("SHA-256:", result_sha)
print(f"[PASS] {audit_state}: {AUDIT.name}")
print("SHA-256:", audit_sha)

print("정책 주장 독립 검증: 0건")
print("수동 문맥 검수: 미완료")
print("원본 변경: 없음")
print("답변·임베딩 승인: False")
print("자동 자격 판정: 비활성화")
print("Git commit·push: 미실행")