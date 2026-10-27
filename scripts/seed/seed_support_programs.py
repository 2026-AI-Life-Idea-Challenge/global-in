
import os
from collections import Counter
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

PROGRAMS = [
    {
        "id": "KR_SUPPORT_KMOVE_SCHOOL",
        "country": "multi_country",
        "name": "해외취업연수 K-Move스쿨",
        "provider": "한국산업인력공단",
        "url": "https://www.worldjob.or.kr/ovsea/sdytrn.do",
        "category": "overseas_employment_training",
        "benefit": "해외취업 연수비 및 취업 연계 지원",
        "target": "해외취업을 희망하는 요건 충족 청년",
        "scope": "해외취업 연수과정별 국가·직종 확인 필요",
        "notes": "연수비 및 참여조건은 과정별·연도별 확인 필요",
    },
    {
        "id": "KR_SUPPORT_SETTLEMENT",
        "country": "multi_country",
        "name": "해외취업정착지원금",
        "provider": "한국산업인력공단",
        "url": (
            "https://www.work24.go.kr/cm/c/f/1100/"
            "selecSystInfo.do?systClId=SC00000204"
            "&systId=SI00000435"
        ),
        "category": "overseas_employment_settlement",
        "benefit": "해외취업자의 현지 정착 지원",
        "target": "공식 사업요건을 충족한 해외취업자",
        "scope": "지원국가 및 취업조건은 해당연도 공고 확인",
        "notes": "소득·근로계약·취업비자 등 요건 별도 검증 필요",
    },
    {
        "id": "KR_US_WEST",
        "country": "usa",
        "name": "한·미 대학생 연수 WEST",
        "provider": "국립국제교육원",
        "url": (
            "https://www.worldjob.or.kr/ovsea/"
            "intern.do?bsnsCd=WP&menuId=1000000043"
        ),
        "category": "overseas_internship",
        "benefit": "미국 어학연수 및 인턴십 참여 지원",
        "target": "모집 회차별 자격요건을 충족하는 지원자",
        "scope": "미국",
        "notes": (
            "기존 programs의 WEST와 연결해 관리할 대상. "
            "모집 회차와 현재 모집 여부는 별도 확인"
        ),
    },
    {
        "id": "KR_US_WEST_LANGUAGE_LOAN",
        "country": "usa",
        "name": "WEST 프로그램 어학연수비 대출",
        "provider": "한국장학재단",
        "url": (
            "https://www.kosaf.go.kr/ko/"
            "tuition.do?pg=PTHDWestAply_01M&ttab1=2"
        ),
        "category": "overseas_internship_financial_support",
        "benefit": "WEST 참가자의 어학연수비 대출 지원",
        "target": "한국장학재단의 회차별 대출 자격 충족자",
        "scope": "미국 WEST 프로그램",
        "notes": (
            "2026년 하반기 신청기간 2026-07-06~2026-08-05 "
            "종료. 다음 회차 일정은 미확인"
        ),
    },
    {
        "id": "KR_SUPPORT_WELL",
        "country": "multi_country",
        "name": "해외일경험지원사업(WELL)",
        "provider": "한국산업인력공단",
        "url": "https://www.worldjob.or.kr/ovsea/well.do",
        "category": "overseas_work_experience",
        "benefit": "해외 현지 일경험, 준비금, 수료금 및 체재비 지원",
        "target": "사업 참여요건과 선발기준을 충족하는 청년",
        "scope": "미국·캐나다·호주·독일·일본 등 사업 대상 국가",
        "notes": "국가별 모집 여부, 비자, 어학요건 및 중복참여 제한 확인 필요",
    },
    {
        "id": "KR_SUPPORT_JOB_MATCHING",
        "country": "multi_country",
        "name": "해외취업알선",
        "provider": "한국산업인력공단",
        "url": "https://www.worldjob.or.kr/ovsea/empymn.do?menuId=1000000040",
        "category": "overseas_job_matching",
        "benefit": "해외 구인기업과 구직자 간 취업 알선 및 매칭",
        "target": "해외취업을 희망하는 구직자",
        "scope": "채용공고별 국가와 직종 확인 필요",
        "notes": "현금 지원사업이 아닌 취업연계 서비스. 공고별 지원자격 검토 필요",
    },
    {
        "id": "KR_SUPPORT_KMOVE_MENTORING",
        "country": "multi_country",
        "name": "K-MOVE 멘토링",
        "provider": "한국산업인력공단",
        "url": "https://kmovefair.worldjob.or.kr/kmove/intro.do",
        "category": "overseas_employment_mentoring",
        "benefit": "해외취업 준비, 현지정보 및 정착 관련 멘토링",
        "target": "해외진출을 준비하는 청년",
        "scope": "멘토별 국가와 분야 확인 필요",
        "notes": "현금 지원사업이 아닌 멘토링 서비스. 모집 및 신청조건 재확인 필요",
    },
]


def main():
    ids = [item["id"] for item in PROGRAMS]
    if len(set(ids)) != len(ids):
        raise RuntimeError("지원제도 ID 중복")

    url_count = Counter(item["url"] for item in PROGRAMS)
    if any(count > 1 for count in url_count.values()):
        raise RuntimeError("공식 출처 URL 중복")

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL 없음")

    with psycopg.connect(db_url) as conn:
        with conn.transaction():
            existing = conn.execute(
                "SELECT COUNT(*) FROM support_programs"
            ).fetchone()[0]

            if existing not in (0,4, len(PROGRAMS)):
                raise RuntimeError(
                    f"예상하지 않은 기존 지원제도 데이터: {existing}건"
                )

            inserted = 0

            for item in PROGRAMS:
                metadata = {
                    "category": item["category"],
                    "benefit_summary": item["benefit"],
                    "target_summary": item["target"],
                    "geographic_scope": item["scope"],
                    "source_url": item["url"],
                    "source_type": "official_public_agency_page",
                    "source_verification": "official_page_identified",
                    "raw_source_archived": False,
                    "eligibility_validation": "needs_review",
                    "recruitment_status": "not_verified_current",
                    "notes": item["notes"],
                    "dataset_stage": "initial_team_share",
                }

                if item["id"] == "KR_US_WEST":
                    metadata["existing_program_relationship"] = (
                        "WEST program; program_id verification pending"
                    )

                if item["id"] == "KR_US_WEST_LANGUAGE_LOAN":
                    metadata["historical_application_window"] = {
                        "start": "2026-07-06",
                        "end": "2026-08-05",
                        "status": "closed",
                    }

                result = conn.execute(
                    """
                    INSERT INTO support_programs (
                        support_program_id,
                        country,
                        name,
                        provider,
                        source_file,
                        review_status,
                        metadata
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (support_program_id)
                    DO NOTHING
                    RETURNING support_program_id
                    """,
                    (
                        item["id"],
                        item["country"],
                        item["name"],
                        item["provider"],
                        None,
                        "needs_review",
                        Jsonb(metadata),
                    ),
                ).fetchone()

                if result:
                    inserted += 1

            support_rows = conn.execute(
                """
                SELECT support_program_id, country,
                       name, review_status, metadata
                FROM support_programs
                ORDER BY support_program_id
                """
            ).fetchall()

            if len(support_rows) != len(PROGRAMS):
                raise RuntimeError("지원제도 적재 개수 불일치")

            by_id = {
                row[0]: row for row in support_rows
            }

            for item in PROGRAMS:
                row = by_id.get(item["id"])
                if row is None:
                    raise RuntimeError(
                        f"지원제도 누락: {item['id']}"
                    )

                _, country, name, status, metadata = row

                if (
                    country != item["country"]
                    or name != item["name"]
                    or status != "needs_review"
                    or metadata.get("source_url") != item["url"]
                ):
                    raise RuntimeError(
                        f"기존 DB 데이터 불일치: {item['id']}"
                    )

            totals = conn.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM programs),
                    (SELECT COUNT(*) FROM policy_candidates),
                    (SELECT COUNT(*) FROM evidence),
                    (SELECT COUNT(*) FROM support_programs)
                """
            ).fetchone()

            if totals != (40, 590, 1241, len(PROGRAMS)):
                raise RuntimeError(
                    f"전체 데이터 수 불일치: {totals}"
                )

            print("=== SUPPORT PROGRAMS RESULT ===")
            print("NEWLY_INSERTED:", inserted)
            print("SUPPORT_PROGRAMS:", totals[3])
            print("PROGRAMS:", totals[0])
            print("POLICIES:", totals[1])
            print("EVIDENCE:", totals[2])
            print("=== SUPPORT PROGRAM LIST ===")

            for sid, country, name, status, _ in support_rows:
                print(sid, "|", country, "|", name, "|", status)

            print("POSTCHECK: PASS")

    print("TRANSACTION: COMMITTED")


if __name__ == "__main__":
    main()