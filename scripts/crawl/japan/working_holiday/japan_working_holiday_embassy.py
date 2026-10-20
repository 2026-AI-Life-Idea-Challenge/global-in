# Path: 파일 및 폴더 경로를 다루는 Python 표준 라이브러리
from pathlib import Path

# BeautifulSoup: HTML에서 필요한 정보를 추출하는 라이브러리
from bs4 import BeautifulSoup


# 1. 현재 Python 파일을 기준으로 프로젝트 루트 찾기
# parents[0] = crawl
# parents[1] = scripts
# parents[2] = global-in
PROJECT_ROOT = Path(__file__).resolve().parents[4]


# 2. Chrome에서 저장한 주한일본대사관 HTML 파일 위치
HTML_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
        / "japan"
        / "working_holiday"
    / "japan_working_holiday_embassy.html"
)


# 3. 파일이 존재하는지 확인
if not HTML_PATH.exists():
    raise FileNotFoundError(
        f"HTML 파일을 찾을 수 없습니다: {HTML_PATH}"
    )


# 4. HTML 파일 읽기
# read_bytes(): 파일을 원본 바이트 데이터로 읽는 메서드
html_content = HTML_PATH.read_bytes()


# 5. BeautifulSoup으로 HTML 분석
soup = BeautifulSoup(html_content, "html.parser")


# 6. 문서 기본 정보 출력
print("===== 주한일본대사관 HTML 확인 =====")
print("파일 존재:", HTML_PATH.exists())
print("HTML 크기:", len(html_content), "bytes")

if soup.title:
    print("페이지 제목:", soup.title.get_text(" ", strip=True))
else:
    print("페이지 제목 없음")


# 7. 문서 제목 구조 확인
print("\n===== 문서 제목 구조 =====")

# h1 ~ h4 제목 태그를 모두 검색
headings = soup.find_all(["h1", "h2", "h3", "h4"])

for index, heading in enumerate(headings, start=1):
    title = heading.get_text(" ", strip=True)

    if title:
        print(f"{index}. [{heading.name}] {title}")


# 8. 본문 텍스트 일부 확인
print("\n===== 본문 미리보기 =====")

if soup.body:
    body_text = soup.body.get_text(" ", strip=True)
    print(body_text[:800])
else:
    print("본문을 찾지 못했습니다.")


# 9. 주한일본대사관의 사증 발급요건 추출하기

print("\n===== 한국인 Working Holiday 사증 발급요건 =====")

# 자격요건 제목을 저장할 변수
eligibility_heading = None

# 이 페이지는 주요 제목이 h1 태그로 작성되어 있음
for heading in soup.find_all("h1"):

    # 제목에서 HTML 태그를 제거하고 텍스트만 추출
    title = heading.get_text(" ", strip=True)

    # 자격요건에 해당하는 제목 찾기
    if "사증 발급요건" in title:
        eligibility_heading = heading
        break


# 추출한 원문을 저장할 리스트
eligibility_texts = []

if eligibility_heading:

    # 제목 다음의 HTML 형제 요소들을 탐색
    for element in eligibility_heading.next_siblings:

        # 다음 h1 제목을 만나면 자격요건 섹션 종료
        if getattr(element, "name", None) == "h1":
            break

        # HTML 태그에 들어 있는 텍스트만 추출
        if hasattr(element, "get_text"):

            text = element.get_text(" ", strip=True)

            # 비어 있지 않은 텍스트만 리스트에 추가
            if text:
                eligibility_texts.append(text)

    # 여러 텍스트를 줄바꿈으로 연결
    eligibility_raw_text = "\n".join(eligibility_texts)

    # 추출 결과 출력
    print(eligibility_raw_text)

    print("\n추출한 글자 수:", len(eligibility_raw_text))

else:
    print("사증 발급요건 섹션을 찾지 못했습니다.")


# 10. 주한일본대사관 자격요건을 JSON 파일로 저장하기

# JSON 파일을 읽고 쓰기 위한 표준 라이브러리
import json

# 현재 시각을 기록하기 위한 라이브러리
from datetime import datetime, timezone


# 1. 저장할 데이터 구성
# 딕셔너리(dict)는 key:value 형태로 데이터를 관리함
embassy_data = {
    "program_id": "jp_working_holiday",

    # 해당 조건을 적용할 대상 국적
    "target_nationality": "South Korea",

    "source": {
        "official_agency": "Embassy of Japan in Korea",
        "source_title": "Working Holiday 사증 안내",
        "source_url": (
            "https://www.kr.emb-japan.go.jp/itpr_ko/visa_working.html"
        ),

        # 대사관 웹페이지에 표시된 날짜
        "page_display_date": "2026-09-30",

        # 데이터를 추출한 시각(UTC)
        "extracted_at": datetime.now(timezone.utc).isoformat()
    },

    # 앞 단계에서 추출한 자격요건 원문
    "eligibility_raw_text": eligibility_raw_text,

    # 아직 개별 조건으로 구조화하지 않은 상태
    "validation_status": "pending_structuring"
}


# 2. JSON 파일 저장 위치
OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
        / "japan"
        / "working_holiday"
    / "japan_working_holiday_embassy_eligibility.json"
)


# 3. JSON 파일 저장
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(
        embassy_data,
        f,
        ensure_ascii=False,  # 한국어를 그대로 저장
        indent=2             # 보기 좋게 들여쓰기
    )


# 4. 저장 결과 확인
print("\n===== 대사관 JSON 저장 결과 =====")
print("파일 경로:", OUTPUT_PATH)
print("파일 존재:", OUTPUT_PATH.exists())
print("원문 길이:", len(eligibility_raw_text))

# 11. 주한일본대사관의 신청수속 섹션 추출하기

print("\n===== 일본 워킹홀리데이 신청수속 =====")

# 신청수속 제목을 저장할 변수
application_heading = None

# 이 페이지의 주요 섹션 제목은 h1 태그를 사용함
for heading in soup.find_all("h1"):

    # 제목 태그에서 실제 글자만 추출
    title = heading.get_text(" ", strip=True)

    # "3. 신청수속"이라는 제목 찾기
    if "3. 신청수속" in title:
        application_heading = heading
        break


# 신청수속 섹션의 내용을 저장할 리스트
application_texts = []

if application_heading:

    # 현재 h1 태그 다음의 형제 요소들을 순서대로 확인
    for element in application_heading.next_siblings:

        # 다음 h1이 나오면 신청수속 섹션이 끝난 것으로 판단
        if getattr(element, "name", None) == "h1":
            break

        # HTML 태그인 경우에만 텍스트 추출
        if hasattr(element, "get_text"):

            text = element.get_text(" ", strip=True)

            # 공백이 아닌 내용만 저장
            if text:
                application_texts.append(text)

    # 여러 텍스트를 줄바꿈으로 연결
    application_raw_text = "\n".join(application_texts)

    # 추출한 내용 출력
    print(application_raw_text)

    # 추출된 글자 수 확인
    print("\n추출한 글자 수:", len(application_raw_text))

else:
    print("신청수속 섹션을 찾지 못했습니다.")

# 12. 제출자료 섹션의 HTML 구조 확인하기

print("\n===== 제출자료 HTML 구조 확인 =====")

# 제출자료 소제목 찾기
documents_heading = None

for heading in soup.find_all("h3"):

    title = heading.get_text(" ", strip=True)

    if "(2) 제출자료" in title:
        documents_heading = heading
        break


# 제출자료 제목을 찾았는지 확인
if documents_heading is None:
    print("제출자료 제목을 찾지 못했습니다.")

else:
    # prettify(): HTML을 들여쓰기하여 보기 좋게 출력
    print("제출자료 제목 HTML:")
    print(documents_heading.prettify())

    # find_next_sibling(): 바로 다음 형제 태그 검색
    next_element = documents_heading.find_next_sibling()

    print("\n제출자료 제목 다음 요소:")

    if next_element is not None:

        # 다음 요소의 태그 이름 확인
        print("태그 이름:", next_element.name)

        # HTML 전체가 너무 길 수 있으므로 앞부분만 출력
        print(next_element.prettify()[:2000])

    else:
        print("다음 형제 요소가 없습니다.")