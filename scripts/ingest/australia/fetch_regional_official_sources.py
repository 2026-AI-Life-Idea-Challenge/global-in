from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
import hashlib
import json

ROOT = Path("data/raw/australia/employment")

BASE = (
    "https://immi.homeaffairs.gov.au/visas/"
    "getting-a-visa/visa-listing/"
)

SOURCES = {
    "subclass_191_regional_provisional": (
        BASE + "skilled-regional-191/regional-provisional"
    ),
    "subclass_491": (
        BASE + "skilled-work-regional-provisional-491"
    ),
    "subclass_494_employer_sponsored": (
        BASE + "skilled-employer-sponsored-regional-494/"
        "employer-sponsored-stream"
    ),
    "subclass_494_labour_agreement": (
        BASE + "skilled-employer-sponsored-regional-494/"
        "labour-agreement-stream"
    ),
}


def collect(context, program_id, url):
    html_path = ROOT / f"{program_id}_rendered.html"
    text_path = ROOT / f"{program_id}_rendered.txt"
    meta_path = ROOT / f"{program_id}_rendered_meta.json"

    if any(p.exists() for p in (html_path, text_path, meta_path)):
        print(f"SKIP_EXISTING: {program_id}")
        return "SKIP"

    page = context.new_page()

    try:
        response = page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=45000,
        )

        status = response.status if response else None

        # JS로 실제 비자 본문이 표시되는지 기다림
        try:
            page.wait_for_function(
                """() => {
                    const b = document.body;
                    if (!b) return false;
                    const t = b.innerText || "";
                    const h = document.querySelectorAll("h1,h2,h3");
                    return t.length > 2500 && h.length >= 2;
                }""",
                timeout=20000,
            )
        except PWTimeout:
            pass

        # 동적 내용의 최종 렌더링 기회 제공
        page.wait_for_timeout(1500)

        title = page.title().strip()
        final_url = page.url
        html = page.content()
        text = page.locator("body").inner_text(timeout=10000)
        headings = page.locator("h1,h2,h3").all_inner_texts()

        subclass = program_id.split("_")[1]
        lower = text.lower()

        domain_ok = (
            urlparse(final_url).hostname
            == "immi.homeaffairs.gov.au"
        )

        checks = {
            "http_ok": status == 200,
            "official_domain": domain_ok,
            "subclass_found": subclass in text,
            "text_length_ok": len(text.strip()) >= 2500,
            "headings_found": len(headings) >= 2,
            "eligibility_found": (
                "eligibility" in lower or "you must" in lower
            ),
            "application_found": (
                "apply" in lower or "step by step" in lower
            ),
        }

        print(f"\nPROGRAM: {program_id}")
        print("HTTP:", status)
        print("FINAL_URL:", final_url)
        print("TITLE:", title)
        print("HTML_BYTES:", len(html.encode("utf-8")))
        print("TEXT_CHARS:", len(text))
        print("HEADINGS:", [h.strip()[:80] for h in headings[:10]])
        print("CHECKS:", checks)

        if not all(checks.values()):
            print("TEXT_PREVIEW:", text[:450].replace("\n", " "))
            print("REVIEW_REQUIRED: Insufficient rendered content")
            return "REVIEW"

        raw = html.encode("utf-8")
        sha = hashlib.sha256(raw).hexdigest()

        meta = {
            "program_id": "AU:" + program_id,
            "source_url": url,
            "final_url": final_url,
            "source_title": title,
            "collected_at_utc": datetime.now(
                timezone.utc
            ).isoformat(),
            "html_sha256": sha,
            "text_chars": len(text),
            "headings": headings,
            "checks": checks,
            "review_status": "needs_review",
            "legal_validation_approved": False,
            "approved_for_eligibility_decision": False,
        }

        # 기존 파일 보호: 새 렌더링 파일만 생성
        with html_path.open("xb") as f:
            f.write(raw)

        with text_path.open("x", encoding="utf-8") as f:
            f.write(text)

        with meta_path.open("x", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        print("PASS:", program_id)
        return "PASS"

    except Exception as e:
        print(
            f"FAIL: {program_id} | "
            f"{type(e).__name__}: {str(e)[:300]}"
        )
        return "FAIL"

    finally:
        page.close()


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    results = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            channel="chrome",
            headless=True,
        )

        try:
            context = browser.new_context(
                locale="en-AU",
                viewport={"width": 1440, "height": 900},
            )

            for program_id, url in SOURCES.items():
                result = collect(context, program_id, url)
                results.append(result)

            context.close()

        finally:
            browser.close()

    print("\n=== AU REGIONAL PLAYWRIGHT BATCH ===")
    print("PASS:", results.count("PASS"))
    print("SKIP_EXISTING:", results.count("SKIP"))
    print("REVIEW_REQUIRED:", results.count("REVIEW"))
    print("FAIL:", results.count("FAIL"))

    print(
        "STATUS:",
        "PASS"
        if results.count("PASS") == len(SOURCES)
        else "REVIEW_REQUIRED",
    )


if __name__ == "__main__":
    main()