
from pathlib import Path
from collections import Counter
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]

BASE = ROOT / "data/processed/japan/employment"

INPUT = BASE / "japan_employment_retrieval_records.jsonl"

OUTPUT = BASE / "japan_employment_search_ready.jsonl"

EXPECTED_INPUT_SHA = (
    "d782f3618d46c951f21a305f40ef72e9"
    "825ee14d77084cad59fb22689c8d8be8"
)

EXPECTED_COUNTS = {
    "coe_common": 6,
    "coe_category34": 8,
    "change": 8,
    "renewal": 13,
}

# 원문 텍스트임이 확인된 필드만 검색 대상으로 사용
TEXT_FIELDS = {
    "raw_text_ja",
    "original_text_ja",
    "intro_original_ja",
    "condition_text_ja",
    "evidence_text_ja",
    "source_text_ja",
    "source_intro_ja",
    "source_note_ja",
    "applicability_condition_ja",
}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def extract_evidence_segments(value, path="evidence", text_fields=None):
    """
    상세 증빙에서 일본어 텍스트를 추출한다.

    - 원본 evidence 수정 없음
    - 원본 JSON 경로 보존
    - 리스트 순서 보존
    - 조건 관계를 자동으로 해석하지 않음
    """
    segments = []
    if text_fields is None:
        text_fields = TEXT_FIELDS

    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"

            if (
                key in text_fields
                and isinstance(child, str)
                and child.strip()
            ):
                segments.append({
                    "source_path": child_path,
                    "text_ja": child,
                })

            elif isinstance(child, (dict, list)):
                segments.extend(
                    extract_evidence_segments(
                        child,
                        child_path,
                        text_fields,
                    )
                )

    elif isinstance(value, list):
        for index, child in enumerate(value):
            segments.extend(
                extract_evidence_segments(
                    child,
                    f"{path}[{index}]",
                    text_fields,
                )
            )

    return segments


def main():
    print("===== STEP 63-99 검색 본문 생성 =====")


    assert INPUT.is_file(), "기존 JSONL 누락"

    # 기존 결과물 덮어쓰기 방지
    assert not OUTPUT.exists(), (
        f"출력 파일이 이미 존재합니다: {OUTPUT}"
    )

    # 1. 입력 무결성 검증
    original_bytes = INPUT.read_bytes()

    assert sha256(original_bytes) == EXPECTED_INPUT_SHA, (
        "입력 JSONL SHA-256 불일치"
    )

    records = [
        json.loads(line)
        for line in original_bytes.decode("utf-8").splitlines()
    ]

    assert len(records) == 35
    print("[PASS] 입력 JSONL SHA-256 및 35개 레코드")

    # 2. 검색 레코드 생성
    search_records = []
    seen_ids = set()
    group_counts = Counter()
    evidence_count = 0
    segment_count = 0

    for record in records:
        document_id = record["document_id"]

        assert document_id == record["record_id"]
        assert document_id not in seen_ids

        seen_ids.add(document_id)

        assert record["route_id"] == "JP-EM"
        assert record["validation_status"] == "needs_review"
        assert (
            record["automatic_eligibility_rules_enabled"]
            is False
        )

        raw_text = record["raw_text_ja"]

        assert isinstance(raw_text, str)
        assert raw_text.strip()

        evidence = record["evidence"]

        assert isinstance(evidence, dict)

        # 상세 증빙 원문을 경로와 함께 추출
        segments = extract_evidence_segments(evidence)

        for segment in segments:
            assert segment["source_path"].startswith("evidence.")
            assert segment["text_ja"].strip()

        if evidence:
            evidence_count += 1

        segment_count += len(segments)

        # 기존 데이터의 모든 필드를 그대로 복사
        # 원본 데이터는 수정하지 않음
        search_record = dict(record)

        # 신규 검색 전용 필드 추가
        search_record["search_text_ja"] = raw_text

        search_record["evidence_search_segments"] = segments

        search_record["search_text_strategy"] = (
            "original_document_text_with_separate_evidence_segments"
        )

        search_record["embedding_generated"] = False

        search_record["validation_status"] = "needs_review"

        search_record[
            "automatic_eligibility_rules_enabled"
        ] = False

        # 기존 필드 보존 검사
        assert all(
            search_record[key] == value
            for key, value in record.items()
        )

        assert search_record["evidence"] == evidence

        search_records.append(search_record)

        group_counts[record["dataset_group"]] += 1

    # 3. 전체 구조 검증
    assert len(search_records) == 35
    assert len(seen_ids) == 35
    assert dict(group_counts) == EXPECTED_COUNTS
    assert evidence_count == 9

    assert all(
        r["search_text_ja"] == r["raw_text_ja"]
        for r in search_records
    )

    assert all(
        r["validation_status"] == "needs_review"
        and r["automatic_eligibility_rules_enabled"] is False
        and r["embedding_generated"] is False
        for r in search_records
    )

    print("[PASS] 검색 본문 35개 구성")
    print("[PASS] 기존 메타데이터 및 상세 증빙 보존")

    # 4. 신규 JSONL 직렬화
    lines = [
        json.dumps(
            record,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        for record in search_records
    ]

    output_bytes = (
        "\n".join(lines) + "\n"
    ).encode("utf-8")

    # 새 파일만 생성하며 덮어쓰기는 허용하지 않음
    with OUTPUT.open("xb") as f:
        f.write(output_bytes)

    # 5. 저장 결과 검증
    saved_bytes = OUTPUT.read_bytes()

    assert saved_bytes == output_bytes
    assert saved_bytes.count(b"\n") == 35
    assert b"\r\n" not in saved_bytes

    saved_records = [
        json.loads(line)
        for line in saved_bytes.decode("utf-8").splitlines()
    ]

    assert saved_records == search_records

    # 6. 입력 불변성 검증
    assert sha256(INPUT.read_bytes()) == EXPECTED_INPUT_SHA

    print("[PASS] 출력 JSONL 저장 및 35줄 검증")
    print("[PASS] 기존 입력 JSONL 불변")

    print("\n[신청 유형별 레코드]")

    for group in EXPECTED_COUNTS:
        print(f"{group}: {group_counts[group]}개")

    print("\n===== STEP 63-99 최종 결과 =====")
    print("검색 본문 레코드:", len(saved_records))
    print("고유 문서 ID:", len(seen_ids))
    print("상세 증빙 연결 레코드:", evidence_count)
    print("추출된 증빙 원문 세그먼트:", segment_count)
    print("검색 본문 언어: 일본어")
    print("출력 파일:", OUTPUT.relative_to(ROOT))
    print("출력 SHA-256:", sha256(saved_bytes))
    print("기존 증빙 구조: 보존")
    print("Category 원본 기호: 보존")
    print("기존 JSONL 변경: 없음")
    print("정책 검증 상태: needs_review")
    print("자동 자격 판정: 비활성화")
    print("임베딩·DB 적재: 미실행")
    print("Git 커밋·푸시: 미실행")

if __name__ == "__main__":
    main()
