# Path: 파일 및 폴더 경로를 다루는 Python 표준 라이브러리
from pathlib import Path

# BeautifulSoup: HTML을 분석하고 필요한 내용을 추출하는 라이브러리
from bs4 import BeautifulSoup


# 1. 현재 Python 파일 위치를 기준으로 프로젝트 루트 찾기
# __file__ : 현재 실행 중인 Python 파일의 경로
# resolve() : 절대 경로로 변환
# parents[0] : crawl 폴더
# parents[1] : scripts 폴더
# parents[2] : global-in 프로젝트 루트
PROJECT_ROOT = Path(__file__).resolve().parents[4]


# 2. Chrome에서 다운로드한 HTML 파일 경로 설정
HTML_PATH = PROJECT_ROOT / "data" / "raw" / "japan" / "working_holiday" / "japan_working_holiday.html"


# 3. 파일 존재 여부 확인
print("파일 경로:", HTML_PATH)
print("파일 존재:", HTML_PATH.exists())

# 파일이 없다면 오류를 발생시키고 실행 중단
if not HTML_PATH.exists():
    raise FileNotFoundError(f"HTML 파일을 찾을 수 없습니다: {HTML_PATH}")


# 4. HTML 파일을 바이너리 모드(rb)로 열어 읽기
# rb: read binary (바이트 단위로 읽기)
# with: 작업 후 파일을 자동으로 닫아줌
with open(HTML_PATH, "rb") as f:
    html_content = f.read()


# 5. BeautifulSoup으로 HTML 분석
# html.parser: Python 기본 HTML 파서
soup = BeautifulSoup(html_content, "html.parser")


# 6. 파일 크기 확인
print("HTML 크기:", len(html_content), "bytes")


# 7. 페이지 제목 추출
if soup.title:
    print("페이지 제목:", soup.title.get_text(strip=True))
else:
    print("페이지 제목 없음")


# 8. 본문 텍스트 일부 출력
# get_text(): HTML 태그를 제거하고 텍스트만 가져옴
# separator=" ": 태그 사이 텍스트를 공백으로 연결
# strip=True: 앞뒤 공백 제거
body = soup.body

if body:
    text = body.get_text(separator=" ", strip=True)
    print("본문 미리보기:", text[:500])
else:
    print("본문을 찾지 못했습니다.")

# 9. HTML에서 문서 제목(Heading) 추출하기
# HTML은 보통 h1 ~ h6 태그를 사용해 제목과 소제목을 구분함
# h1: 가장 상위 제목
# h2: 중간 제목
# h3: 하위 제목

print("\n===== 문서 제목 구조 =====")

# find_all(): 조건에 맞는 HTML 태그를 모두 검색
# 아래 코드는 h1, h2, h3, h4 태그를 찾음
headings = soup.find_all(["h1", "h2", "h3", "h4"])

# enumerate(): 순회하면서 번호를 함께 생성
# start=1: 번호를 1부터 시작
for index, heading in enumerate(headings, start=1):

    # heading.name: HTML 태그 이름 (h1, h2 등)
    tag_name = heading.name

    # 제목에서 HTML 태그를 제외한 텍스트 추출
    title = heading.get_text(" ", strip=True)

    # 실제 텍스트가 존재하는 제목만 출력
    if title:
        print(f"{index}. [{tag_name}] {title}")

# 10. Eligibility 섹션 찾기
# find_all("h2"): 문서에 있는 모든 h2 제목을 검색
# next_siblings: 특정 태그 뒤에 나오는 형제 요소들을 순서대로 탐색

print("\n===== Eligibility 원문 =====")

# Eligibility 제목을 저장할 변수
eligibility_heading = None

# 모든 h2 제목 중 Eligibility가 포함된 제목 찾기
for heading in soup.find_all("h2"):

    title = heading.get_text(" ", strip=True)

    if "Eligibility to participate" in title:
        eligibility_heading = heading
        break  # 원하는 제목을 찾았으므로 반복 종료


# 제목을 찾은 경우에만 본문 추출
if eligibility_heading:

    # 해당 h2 뒤에 나오는 형제 태그 순회
    for element in eligibility_heading.next_siblings:

        # 다음 h2 제목이 나오면 현재 섹션 종료
        if getattr(element, "name", None) == "h2":
            break

        # HTML 태그에 포함된 텍스트 추출
        if hasattr(element, "get_text"):

            text = element.get_text(" ", strip=True)

            if text:
                print(text)

else:
    print("Eligibility 섹션을 찾지 못했습니다.")

# 11. 추출한 Eligibility 원문을 JSON 파일로 저장하기

# json: Python 데이터를 JSON 형식으로 저장하는 표준 라이브러리
import json

# datetime: 현재 날짜와 시간을 기록하는 표준 라이브러리
from datetime import datetime, timezone


# 1. Eligibility 섹션의 텍스트를 저장할 리스트
eligibility_texts = []

if eligibility_heading:

    # Eligibility 제목 다음부터 다음 h2 전까지 탐색
    for element in eligibility_heading.next_siblings:

        # 다음 h2를 만나면 현재 섹션 종료
        if getattr(element, "name", None) == "h2":
            break

        # HTML 태그인 경우에만 텍스트 추출
        if hasattr(element, "get_text"):
            text = element.get_text(" ", strip=True)

            if text:
                eligibility_texts.append(text)


# 2. 여러 텍스트를 하나의 문자열로 결합
# "\n"은 줄바꿈 문자
eligibility_raw_text = "\n".join(eligibility_texts)


# 3. JSON으로 저장할 데이터 구성
data = {
    "program_id": "jp_working_holiday",
    "destination_country": "Japan",
    "program_type": "working_holiday",

    "source": {
        "official_agency": "Ministry of Foreign Affairs of Japan",
        "source_title": (
            "The Working Holiday Programmes in Japan"
        ),
        "source_url": (
            "https://www.mofa.go.jp/j_info/visit/w_holiday/"
        ),
        "source_type": "official_guide",

        # 원문 페이지에 표시된 날짜
        # 실제 수정일인지 별도 검증 전이므로 게시/수정일로 확정하지 않음
        "page_display_date": "2026-04-01",

        # 현재 시각을 UTC 기준으로 기록
        "extracted_at": datetime.now(timezone.utc).isoformat()
    },

    # 공식 원문을 가공하지 않고 저장
    "eligibility_raw_text": eligibility_raw_text,

    # 아직 한국 공관과 대조하지 않은 상태
    "validation_status": "needs_review"
}


# 4. JSON 저장 경로 설정
OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
        / "japan"
        / "working_holiday"
    / "japan_working_holiday_eligibility.json"
)


# 5. JSON 파일 저장
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(
        data,
        f,
        ensure_ascii=False,  # 한국어와 일본어를 그대로 저장
        indent=2             # 보기 좋게 들여쓰기
    )


# 6. 저장 결과 확인
print("\n===== JSON 저장 결과 =====")
print("저장 경로:", OUTPUT_PATH)
print("파일 존재:", OUTPUT_PATH.exists())
print("추출 텍스트 길이:", len(eligibility_raw_text))

# 12. 저장한 JSON 파일을 다시 읽고 데이터 검증하기

# JSON 파일 열기
# encoding="utf-8": 한글과 일본어 등의 문자를 정상적으로 읽기 위한 설정
with open(OUTPUT_PATH, "r", encoding="utf-8") as f:

    # json.load(): JSON 파일을 Python 딕셔너리로 변환
    saved_data = json.load(f)


print("\n===== JSON 데이터 검증 =====")

# get(): 딕셔너리에서 해당 키의 값을 가져옴
# 키가 없다면 오류 대신 None을 반환
print("프로그램 ID:", saved_data.get("program_id"))
print("국가:", saved_data.get("destination_country"))
print("프로그램 유형:", saved_data.get("program_type"))

# 중첩된 딕셔너리 접근
source = saved_data.get("source", {})

print("공식 출처:", source.get("official_agency"))
print("출처 URL:", source.get("source_url"))

# 원문 텍스트 확인
raw_text = saved_data.get("eligibility_raw_text", "")

print("원문 길이:", len(raw_text))

# 원문에서 중요한 키워드가 존재하는지 검사
# 주의: 단어의 존재 여부만 확인하며 자격 충족 여부를 판정하지는 않음
keywords = [
    "South Korea",
    "18 and 25",
    "passport",
    "funds",
    "1 October, 2025"
]

for keyword in keywords:

    # in 연산자: 문자열 안에 특정 단어가 포함되어 있는지 검사
    found = keyword in raw_text

    print(f"'{keyword}' 포함 여부: {found}")

# 13. Eligibility 원문에서 한국 관련 문장 찾기

# re: 정규표현식을 이용해 문자열을 검색·분리하는 표준 라이브러리
import re

print("\n===== 한국 관련 Eligibility 문장 =====")

# 문장 끝의 마침표, 세미콜론 등을 기준으로 텍스트 분리
# re.split(): 정규표현식 패턴을 기준으로 문자열을 나눔
sentences = re.split(r"(?<=[.;])\s+", raw_text)

# 한국 관련 문장을 담을 리스트
korea_sentences = []

for sentence in sentences:

    # 대소문자를 무시하고 South Korea가 포함된 문장 검색
    if "south korea" in sentence.lower():
        korea_sentences.append(sentence.strip())

# 추출된 문장을 번호와 함께 출력
for index, sentence in enumerate(korea_sentences, start=1):
    print(f"\n{index}. {sentence}")

# 검색 결과가 없는 경우 확인
if not korea_sentences:
    print("한국 관련 문장을 찾지 못했습니다.")

# 14. 한국 국적자 관련 원문을 별도 JSON으로 저장하기

# 저장할 JSON 데이터 구성
korea_data = {
    "program_id": "jp_working_holiday",

    # 데이터를 적용할 대상 국적
    "target_nationality": "South Korea",

    # 데이터를 가져온 공식 출처
    "source_url": saved_data["source"]["source_url"],

    # 앞 단계에서 추출한 한국 관련 문장 리스트
    "country_specific_evidence": korea_sentences,

    # 한국 공관의 상세 조건과 대조하기 전 상태
    "validation_status": "needs_embassy_review"
}

# 저장 경로 설정
# PROJECT_ROOT는 이전 단계에서 정의한 프로젝트 루트
KOREA_OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
        / "japan"
        / "working_holiday"
    / "japan_working_holiday_korea.json"
)

# 부모 폴더가 없다면 생성
# parents=True: 상위 폴더까지 필요한 경우 생성
# exist_ok=True: 이미 폴더가 있어도 오류를 발생시키지 않음
KOREA_OUTPUT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True
)

# JSON 파일로 저장
with open(KOREA_OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(
        korea_data,
        f,
        ensure_ascii=False,
        indent=2
    )

# 저장 결과 확인
print("\n===== 한국 관련 데이터 저장 =====")
print("저장 경로:", KOREA_OUTPUT_PATH)
print("파일 존재:", KOREA_OUTPUT_PATH.exists())
print("한국 관련 문장 수:", len(korea_sentences))