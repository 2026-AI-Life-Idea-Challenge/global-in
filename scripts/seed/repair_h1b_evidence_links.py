
import argparse
import hashlib
import html
import os
import re
import pymupdf
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

import psycopg
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from psycopg.types.json import Jsonb


ROOT = Path(__file__).resolve().parents[2]
SOURCE_ROOT = (
    ROOT
    / "data"
    / "raw"
    / "usa"
    / "employment"
    / "h1b_specialty_occupation"
)

PROGRAM_ID = "US:US-EM-01"

DOS_SOURCE_PATH = (
    ROOT
    / "data"
    / "raw"
    / "usa"
    / "employment"
    / "l1_intracompany_transferee"
    / "state_department_temporary_worker_visas.html"
)

DOS_SOURCE_URL = (
    "https://travel.state.gov/content/travel/en/"
    "us-visas/employment/temporary-worker-visas.html"
)

USCIS_MEMO_PATH = (
    SOURCE_ROOT / "uscis_h1b_2025_proclamation_memo.pdf"
)

USCIS_MEMO_URL = (
    "https://www.uscis.gov/sites/default/files/"
    "document/memos/H1B_Proc_Memo_FINAL.pdf"
)

# canonical URL이 없는 Federal Register HTML은
# 공식 문서번호와 파일명을 함께 검증한다.
DOCUMENT_MAP = {
    "dhs_h1b_modernization_final_rule_2024.html": "2024-29354",
    "h1b_entry_restriction_proclamation_2026.html": "2026-19554",
    "dhs_h1b_biometric_fee_final_rule_2026.html": "2026-16231",
}


def normalize_text(value):
    return re.sub(
        r"\s+",
        " ",
        html.unescape(value or ""),
    ).strip().casefold()


def normalize_url(value):
    if not isinstance(value, str):
        return None

    parsed = urlsplit(value)

    if parsed.scheme not in ("http", "https"):
        return None

    return (
        parsed.netloc.lower(),
        parsed.path.rstrip("/"),
    )


def load_pages():
    pages = {}

    for path in sorted(list(SOURCE_ROOT.glob("*.html")) + [DOS_SOURCE_PATH]):
        if not path.is_file():
            raise FileNotFoundError(path)
        raw = path.read_bytes()
        content = raw.decode("utf-8", errors="replace")
        soup = BeautifulSoup(content, "html.parser")

        canonical = soup.find("link", rel="canonical")
        og_url = soup.find(
            "meta",
            attrs={"property": "og:url"},
        )

        declared_urls = []

        if canonical and canonical.get("href"):
            declared_urls.append(canonical["href"])

        if og_url and og_url.get("content"):
            declared_urls.append(og_url["content"])

        pages[path.name] = {
            "path": path,
            "text": normalize_text(
                soup.get_text(" ", strip=True)
            ),
            "raw": content,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "declared_urls": declared_urls,
        }
    # 기존 USCIS PDF를 Evidence 검색 대상으로 추가
    if not USCIS_MEMO_PATH.is_file():
        raise FileNotFoundError(USCIS_MEMO_PATH)

    pdf_bytes = USCIS_MEMO_PATH.read_bytes()

    if not pdf_bytes.startswith(b"%PDF-"):
        raise ValueError("Invalid USCIS PDF file")

    with pymupdf.open(
        stream=pdf_bytes,
        filetype="pdf",
    ) as document:
        pdf_text = " ".join(
            page.get_text("text")
            for page in document
        )

    pages[USCIS_MEMO_PATH.name] = {
        "path": USCIS_MEMO_PATH,
        "text": normalize_text(pdf_text),
        "raw": pdf_text,
        "sha256": hashlib.sha256(pdf_bytes).hexdigest(),
        "declared_urls": [],
    }

    return pages



def verify_source(page_name, page, source_url):
    expected = normalize_url(source_url)

    if expected is None:
        return None
    # USCIS PDF: 로컬 원문 일치와 정책의 공식 URL 대응 확인
    if page_name == USCIS_MEMO_PATH.name:
        if expected != normalize_url(USCIS_MEMO_URL):
            return None

        if page["path"] != USCIS_MEMO_PATH:
            return None

        return "local_uscis_pdf_excerpt_match"

    # 미국 국무부 Temporary Worker Visas
    # canonical URL이 없는 로컬 HTML의 출처 확인
    if page_name == DOS_SOURCE_PATH.name:
        if expected != normalize_url(DOS_SOURCE_URL):
            return None

        soup = BeautifulSoup(page["raw"], "html.parser")

        title = (
            soup.title.get_text(" ", strip=True)
            if soup.title
            else ""
        )

        if title != "Temporary Worker Visas":
            return None

        raw_lower = page["raw"].lower()

        if "travel.state.gov" not in raw_lower:
            return None

        if "temporary-worker-visas" not in raw_lower:
            return None

        return "local_page_identity_match"

    # canonical URL 또는 og:url이 있는 HTML
    if any(
        normalize_url(url) == expected
        for url in page["declared_urls"]
    ):
        return "canonical_url_match"

    # Federal Register / GovInfo 문서번호 기반 확인
    document_number = DOCUMENT_MAP.get(page_name)

    if document_number is None:
        return None

    if document_number not in source_url:
        return None

    if document_number not in page["raw"]:
        return None

    if expected[0] not in (
        "www.govinfo.gov",
        "govinfo.gov",
        "www.federalregister.gov",
        "federalregister.gov",
    ):
        return None

    return "federal_register_document_match"

# DHS 2024 H-1B Modernization Final Rule
# 최종 규정 본문의 시작/끝 문구를 지정한다.
DHS_QUOTE_RANGES = {
    "MOD-001": (
        "At the time of filing, the petitioner must establish",
        "A petitioner is not required to establish specific day-to-day assignments for the entire time requested in the petition.",
    ),
    "MOD-002": (
        "USCIS will determine whether the labor condition application involves a specialty occupation",
        "properly corresponds with the petition.",
    ),
    "MOD-003": (
        "If USCIS is unable to verify facts, including due to the failure or refusal",
        "including any third party worksites.",
    ),
    "MOD-004": (
        "(2) Has a legal presence in the United States",
        "(3) Has an Internal Revenue Service Tax identification number.",
    ),
    "MOD-005": (
        "(3) Third party requirements. If the beneficiary",
        "when determining whether the position is a specialty occupation.",
    ),
    "MOD-006": (
        "(4) If the H-1B beneficiary possesses a controlling interest",
        "consistent with the terms of the H-1B petition.",
    ),
    "MOD-007": (
        "will qualify for an exemption under such section if the H-1B beneficiary",
        "rather than where the duties are physically performed.",
    ),
    "MOD-008": (
        "(ii) Immediate and automatic revocation.",
        "the beneficiary is no longer employed.",
    ),
    "MOD-009": (
        "(D)(1) If an H-1B petition is adjudicated",
        "from that originally indicated in their petition.",
    ),
}


def extract_dhs_quote(policy_id, page):
    suffix = policy_id.rsplit("POL-", 1)[-1]
    anchors = DHS_QUOTE_RANGES.get(suffix)

    if anchors is None:
        return None

    soup = BeautifulSoup(page["raw"], "html.parser")
    full_text = re.sub(
        r"\s+",
        " ",
        html.unescape(soup.get_text(" ", strip=True)),
    ).strip()

    # 최종 규정 본문에 한정한다.
    offset = max(0, len(full_text) - 45000)
    section = full_text[offset:]
    search_text = section.casefold()

    start_anchor, end_anchor = anchors
    start_key = start_anchor.casefold()
    end_key = end_anchor.casefold()

    if search_text.count(start_key) != 1:
        return None

    start = search_text.find(start_key)
    end = search_text.find(
        end_key,
        start + len(start_key),
    )

    if end < 0:
        return None

    end += len(end_key)

    if end - start > 3500:
        return None

    # MOD-004는 앞의 고용 제의 요건까지 포함한다.
    if suffix == "MOD-004":
        previous = search_text.rfind(
            "(1)",
            max(0, start - 500),
            start,
        )
        if previous < 0:
            return None
        start = previous

    # MOD-007은 Cap 면제 대상 설명을 포함한다.
    if suffix == "MOD-007":
        start = max(0, start - 220)

    quote = section[start:end].strip()

    return {
        "exact_quote": quote,
        "source_location": (
            f"2024-29354 final regulatory text; "
            f"normalized_text_offset={offset + start}:{offset + end}"
        ),
    }

def prepare(conn):
    pages = load_pages()

    policies = conn.execute(
        """
        SELECT policy_id, metadata
        FROM policy_candidates
        WHERE program_id = %s
          AND cardinality(source_evidence_ids) = 0
        ORDER BY policy_id
        """,
        (PROGRAM_ID,),
    ).fetchall()

    prepared = []
    excluded = Counter()

    for policy_id, metadata in policies:
        metadata = metadata or {}
        original = metadata.get("original_policy") or {}
        excerpt = original.get("evidence_excerpt")


        # 영어 발췌문이 없는 DHS 현대화 규정 9건 복구
        if (
            policy_id.endswith(tuple(DHS_QUOTE_RANGES))
            and not excerpt
        ):
            page_name = "dhs_h1b_modernization_final_rule_2024.html"
            page = pages[page_name]

            source_url = metadata.get("source_url")
            verification = verify_source(
                page_name,
                page,
                source_url,
            )

            extracted = extract_dhs_quote(policy_id, page)

            if verification is None or extracted is None:
                excluded["dhs_quote_unverified"] += 1
                continue

            evidence_id = f"US:H1B:RECOVERED:{policy_id}"

            prepared.append({
                "policy_id": policy_id,
                "evidence_id": evidence_id,
                "source_url": source_url,
                "source_file": (
                    page["path"].relative_to(ROOT).as_posix()
                ),
                "source_sha256": page["sha256"],
                "exact_quote": extracted["exact_quote"],
                "source_location": extracted["source_location"],
                "metadata": {
                    "dataset_type": "h1b_modernization_recovered",
                    "original_source_id": metadata.get("source_id"),
                    "local_html_sha256": page["sha256"],
                    "source_verification_method": verification,
                    "quote_selection_method": "anchored_regulatory_text",
                    "source_location": extracted["source_location"],
                    "legal_validation_status": "needs_review",
                    "current_policy_verified": False,
                    "automatic_eligibility_rules_enabled": False,
                    "approved_for_user_answers": False,
                },
            })
            continue

        if not isinstance(excerpt, str) or not excerpt.strip():
            excluded["no_excerpt"] += 1
            continue

        matches = [
            (name, page)
            for name, page in pages.items()
            if normalize_text(excerpt) in page["text"]
        ]

        if len(matches) != 1:
            excluded["not_unique_html_match"] += 1
            continue

        page_name, page = matches[0]

        excerpt_hash = hashlib.sha256(
            excerpt.encode("utf-8")
        ).hexdigest()

        if excerpt_hash != original.get("excerpt_sha256"):
            excluded["excerpt_hash_mismatch"] += 1
            continue

        source_url = metadata.get("source_url")

        source_method = verify_source(
            page_name,
            page,
            source_url,
        )

        if source_method is None:
            excluded["source_identity_unverified"] += 1
            continue

        evidence_id = f"US:H1B:RECOVERED:{policy_id}"

        evidence_metadata = {
            "dataset_type": "h1b_recovered_policy_evidence",
            "source_policy_id": policy_id,
            "original_source_id": metadata.get("source_id"),
            "original_excerpt_sha256": excerpt_hash,
            "local_html_sha256": page["sha256"],
            "source_verification_method": source_method,
            "source_excerpt_verbatim": True,
            "legal_validation_status": "needs_review",
            "current_policy_verified": False,
            "automatic_eligibility_rules_enabled": False,
            "approved_for_user_answers": False,
        }

        source_file = page["path"].relative_to(ROOT).as_posix()

        prepared.append({
            "policy_id": policy_id,
            "evidence_id": evidence_id,
            "source_url": source_url,
            "source_file": source_file,
            "source_sha256": page["sha256"],
            "exact_quote": excerpt,
            "metadata": evidence_metadata,
        })

    return policies, prepared, excluded


def main():
    parser = argparse.ArgumentParser()

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--insert", action="store_true")

    args = parser.parse_args()

    load_dotenv(ROOT / ".env")

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is missing")

    with psycopg.connect(database_url) as conn:
        policies, prepared, excluded = prepare(conn)

        ids = [item["evidence_id"] for item in prepared]

        existing = conn.execute(
            """
            SELECT evidence_id
            FROM evidence
            WHERE evidence_id = ANY(%s)
            """,
            (ids,),
        ).fetchall()

        print("=== H1B EVIDENCE RECOVERY VALIDATION ===")
        print("Unlinked policies:", len(policies))
        print("Ready:", len(prepared))
        print("Excluded:", sum(excluded.values()))
        print("Exclusion reasons:", dict(excluded))
        print("Existing ID conflicts:", len(existing))
        print(
            "Source verification:",
            dict(Counter(
                item["metadata"]["source_verification_method"]
                for item in prepared
            )),
        )

        if len(policies) != 9:
            raise ValueError(
                "Unexpected number of unlinked H-1B policies"
            )

        if len(prepared) != 9:
            raise ValueError(
                "Expected exactly 2 verified Evidence records"
            )

        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate recovery Evidence IDs")

        if existing:
            raise ValueError(
                "Recovery Evidence IDs already exist"
            )

        if args.check:
            print("Mode: CHECK ONLY")
            print("Database modified: False")
            return

        inserted = 0
        linked = 0

        for item in prepared:
            conn.execute(
                """
                INSERT INTO evidence (
                    evidence_id,
                    program_id,
                    country,
                    source_evidence_id,
                    source_id,
                    source_url,
                    source_file,
                    source_sha256,
                    exact_quote,
                    source_location,
                    review_status,
                    metadata
                )
                VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s
                )
                """,
                (
                    item["evidence_id"],
                    PROGRAM_ID,
                    "usa",
                    item["policy_id"],
                    item["metadata"]["original_source_id"],
                    item["source_url"],
                    item["source_file"],
                    item["source_sha256"],
                    item["exact_quote"],
                    item.get(
                        "source_location",
                        f"policy={item['policy_id']}",
                    ),
                    "needs_review",
                    Jsonb(item["metadata"]),
                ),
            )

            inserted += 1

            result = conn.execute(
                """
                UPDATE policy_candidates
                SET source_evidence_ids = ARRAY[%s]::text[]
                WHERE policy_id = %s
                  AND program_id = %s
                  AND cardinality(source_evidence_ids) = 0
                  AND review_status = 'needs_review'
                  AND NOT legal_validation_approved
                  AND NOT approved_for_eligibility_decision
                  AND NOT approved_for_embedding
                  AND NOT approved_for_user_answers
                """,
                (
                    item["evidence_id"],
                    item["policy_id"],
                    PROGRAM_ID,
                ),
            )

            if result.rowcount != 1:
                raise RuntimeError(
                    f"Policy link update failed: {item['policy_id']}"
                )

            linked += 1

        remaining = conn.execute(
            """
            SELECT COUNT(*)
            FROM policy_candidates
            WHERE program_id = %s
              AND cardinality(source_evidence_ids) = 0
            """,
            (PROGRAM_ID,),
        ).fetchone()[0]

        if remaining != 0:
            raise RuntimeError(
                f"Unexpected remaining unlinked policies: {remaining}"
            )

        print("=== H1B RECOVERY RESULT ===")
        print("Inserted Evidence:", inserted)
        print("Linked policies:", linked)
        print("Remaining unlinked:", remaining)
        print("Approval flags modified: False")


if __name__ == "__main__":
    main()