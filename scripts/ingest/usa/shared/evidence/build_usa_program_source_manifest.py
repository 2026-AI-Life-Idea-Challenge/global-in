
from pathlib import Path
from datetime import date
import hashlib
import json

ROOT = Path(__file__).resolve().parents[5]
OUTPUT = ROOT / "data/raw/usa/usa_program_source_manifest.json"

PROGRAMS = [
    {
        "program_id": "US-WH-01",
        "route_id": "US-WH",
        "official_program_name": "Summer Work Travel",
        "visa_classification": "J-1",
        "sources": [
            {
                "source_type": "official_program_page",
                "agency": "U.S. Department of State - BridgeUSA",
                "url": "https://j1visa.state.gov/programs/summer-work-travel/",
            },
            {
                "source_type": "visa_procedure",
                "agency": "U.S. Department of State",
                "url": "https://travel.state.gov/content/travel/en/us-visas/study/exchange.html",
            },
        ],
    },
    {
        "program_id": "US-ST-01",
        "route_id": "US-ST",
        "official_program_name": "Academic Student",
        "visa_classification": "F-1",
        "sources": [
            {
                "source_type": "visa_procedure",
                "agency": "U.S. Department of State",
                "url": "https://travel.state.gov/content/travel/en/us-visas/study/student-visa.html",
            },
        ],
    },
    {
        "program_id": "US-ST-03",
        "route_id": "US-ST",
        "official_program_name": "College and University Student",
        "visa_classification": "J-1",
        "sources": [
            {
                "source_type": "official_program_page",
                "agency": "U.S. Department of State - BridgeUSA",
                "url": "https://j1visa.state.gov/programs/college-and-university-student/",
            },
            {
                "source_type": "visa_procedure",
                "agency": "U.S. Department of State",
                "url": "https://travel.state.gov/content/travel/en/us-visas/study/exchange.html",
            },
        ],
    },
    {
        "program_id": "US-EM-01",
        "route_id": "US-EM",
        "official_program_name": "H-1B Specialty Occupations",
        "visa_classification": "H-1B",
        "sources": [
            {
                "source_type": "visa_procedure",
                "agency": "U.S. Department of State",
                "url": "https://travel.state.gov/content/travel/en/us-visas/employment/temporary-worker-visas.html",
            },
        ],
    },
    {
        "program_id": "US-EM-02",
        "route_id": "US-EM",
        "official_program_name": "Intern",
        "visa_classification": "J-1",
        "sources": [
            {
                "source_type": "official_program_page",
                "agency": "U.S. Department of State - BridgeUSA",
                "url": "https://j1visa.state.gov/programs/intern/",
            },
            {
                "source_type": "visa_procedure",
                "agency": "U.S. Department of State",
                "url": "https://travel.state.gov/content/travel/en/us-visas/study/exchange.html",
            },
        ],
    },
    {
        "program_id": "US-EM-03",
        "route_id": "US-EM",
        "official_program_name": "Trainee",
        "visa_classification": "J-1",
        "sources": [
            {
                "source_type": "official_program_page",
                "agency": "U.S. Department of State - BridgeUSA",
                "url": "https://j1visa.state.gov/programs/trainee/",
            },
            {
                "source_type": "visa_procedure",
                "agency": "U.S. Department of State",
                "url": "https://travel.state.gov/content/travel/en/us-visas/study/exchange.html",
            },
        ],
    },
    {
        "program_id": "US-WEST-01",
        "route_id": "US-EM",
        "related_routes": ["US-WH", "US-ST"],
        "official_program_name": "WEST (Work, English Study, Travel)",
        "visa_classification": "J-1 (program-associated)",
        "sources": [
            {
                "source_type": "official_program_page",
                "agency": "National Institute for International Education",
                "url": "https://niied.go.kr/web/niied/contents/niied_iee_west",
            },
            {
                "source_type": "historical_recruitment_notice",
                "agency": "National Institute for International Education",
                "url": "https://www.niied.go.kr/web/main/nid/niied_board/5570",
            },
        ],
    },
]

EXPECTED_IDS = {
    "US-WH-01",
    "US-ST-01",
    "US-ST-03",
    "US-EM-01",
    "US-EM-02",
    "US-EM-03",
    "US-WEST-01",
}

print("===== STEP 64-03A 미국 공식 출처 Manifest 생성 =====")

assert len(PROGRAMS) == 7
assert {p["program_id"] for p in PROGRAMS} == EXPECTED_IDS

source_count = 0
unique_urls = set()

for program in PROGRAMS:
    assert program["route_id"] in {"US-WH", "US-ST", "US-EM"}
    assert program["sources"]

    program["nationality_scope"] = ["KR"]
    program["korean_applicability_status"] = (
        "individual_review_required"
    )
    program["validation_status"] = "needs_review"
    program["automatic_eligibility_rules_enabled"] = False

    for source in program["sources"]:
        assert source["url"].startswith("https://")
        assert source["agency"]
        assert source["source_type"]

        source["content_downloaded"] = False
        source["content_sha256"] = None
        source["last_checked_at"] = None
        source["content_validation_status"] = "not_collected"

        source_count += 1
        unique_urls.add(source["url"])

assert source_count == 12
assert len(unique_urls) == 9

print("[PASS] 프로그램 ID 7개")
print("[PASS] 공식 출처 연결 12개")
print("[PASS] 고유 공식 URL 9개")
print("[PASS] 정책 판정 비활성화")

manifest = {
    "dataset_id": "US_PROGRAM_SOURCE_MANIFEST_V1",
    "country": "US",
    "target_nationality": "KR",
    "purpose": "official_source_inventory",
    "program_count": len(PROGRAMS),
    "source_link_count": source_count,
    "unique_source_url_count": len(unique_urls),
    "source_content_collected": False,
    "validation_status": "needs_review",
    "automatic_eligibility_rules_enabled": False,
    "programs": PROGRAMS,
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

payload = (
    json.dumps(
        manifest,
        ensure_ascii=False,
        indent=2,
    ) + "\n"
).encode("utf-8")

# 기존 파일을 덮어쓰지 않음
with OUTPUT.open("xb") as f:
    f.write(payload)

assert OUTPUT.read_bytes() == payload

loaded = json.loads(OUTPUT.read_text(encoding="utf-8"))
assert loaded == manifest

digest = hashlib.sha256(payload).hexdigest()

print("[PASS] Manifest JSON 저장")
print("[PASS] 저장 후 JSON 일치 검증")
print("[PASS] 원본 HTML·PDF 다운로드 없음")

print("\n===== STEP 64-03A 최종 결과 =====")
print("프로그램:", len(PROGRAMS))
print("출처 연결:", source_count)
print("고유 공식 URL:", len(unique_urls))
print("저장 파일:", OUTPUT.relative_to(ROOT))
print("SHA-256:", digest)
print("정책 검증: needs_review")
print("자격 자동 판정: 비활성화")
print("Git 커밋·푸시: 미실행")