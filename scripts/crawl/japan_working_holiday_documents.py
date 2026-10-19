# Path: 파일이나 폴더의 경로를 다루는 Python 표준 라이브러리
from pathlib import Path

# BeautifulSoup: HTML 문서를 분석하고 필요한 데이터를 추출하는 라이브러리
from bs4 import BeautifulSoup


# 1. 프로젝트 최상위 폴더 경로 찾기
# __file__ : 현재 실행 중인 Python 파일의 경로
# resolve() : 경로를 절대 경로로 변환
# parents[2] : global-in 프로젝트 최상위 폴더
PROJECT_ROOT = Path(__file__).resolve().parents[2]


# 2. 다운로드한 제출서류 HTML 파일 경로 지정
HTML_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "japan_working_holiday_documents.html"
)


# 3. 파일 존재 여부 확인
# exists() : 파일이나 폴더가 존재하면 True 반환
if not HTML_PATH.exists():
    raise FileNotFoundError(
        f"HTML 파일을 찾을 수 없습니다: {HTML_PATH}"
    )


# 4. HTML 파일 읽기
# read_bytes() : 파일 내용을 바이트(bytes) 형태로 읽음
html_content = HTML_PATH.read_bytes()


# 5. HTML을 BeautifulSoup 객체로 변환
# html.parser : Python에 내장된 HTML 분석기
soup = BeautifulSoup(html_content, "html.parser")


# 6. 파일과 페이지 기본 정보 출력
print("===== 제출서류 HTML 확인 =====")
print("파일 존재:", HTML_PATH.exists())
print("파일 크기:", len(html_content), "bytes")

if soup.title:
    print("페이지 제목:", soup.title.get_text(" ", strip=True))
else:
    print("페이지 제목 없음")


# 7. 문서에 사용된 제목 태그 확인
print("\n===== 문서 제목 구조 =====")

# find_all() : 지정한 태그를 모두 검색
headings = soup.find_all(["h1", "h2", "h3", "h4"])

# enumerate() : 각 요소에 번호를 붙여 반복
for index, heading in enumerate(headings, start=1):

    title = heading.get_text(" ", strip=True)

    if title:
        print(f"{index}. [{heading.name}] {title}")


# 8. HTML에서 목록과 표의 개수 확인
# 제출서류가 ul, ol, li 또는 table 태그에 들어 있는지 파악
print("\n===== HTML 태그 개수 =====")

for tag_name in ["ul", "ol", "li", "table", "tr"]:

    # len() : 검색된 태그 개수 계산
    count = len(soup.find_all(tag_name))

    print(f"{tag_name} 태그: {count}개")


# 9. 본문 내용 일부 출력
print("\n===== 제출서류 본문 미리보기 =====")

if soup.body:

    # get_text() : HTML 태그를 제거하고 텍스트만 추출
    # separator="\n" : 태그 사이를 줄바꿈으로 구분
    body_text = soup.body.get_text(separator="\n", strip=True)

    # 처음 1500자만 출력
    print(body_text[:1500])

else:
    print("본문을 찾지 못했습니다.")

# 10. 필수 제출서류 목록 추출하기

# Tag: BeautifulSoup에서 실제 HTML 태그인지 확인할 때 사용
from bs4 import Tag

print("\n===== 필수 제출서류 목록 =====")

# 1. '★ 필수자료' 제목 찾기
required_heading = None

for heading in soup.find_all("h1"):

    title = heading.get_text(" ", strip=True)

    if "필수자료" in title:
        required_heading = heading
        break


# 2. 필수자료 섹션 내부의 목록을 저장할 리스트
required_documents = []

if required_heading is None:
    print("필수자료 제목을 찾지 못했습니다.")

else:
    # 다음 h1 제목이 나올 때까지 형제 요소 탐색
    for element in required_heading.next_siblings:

        # 문자열 등의 요소는 제외하고 HTML 태그만 처리
        if not isinstance(element, Tag):
            continue

        # 다음 h1을 만나면 필수자료 섹션 종료
        if element.name == "h1":
            break

        # ol(순서 있는 목록) 태그 검색
        # 현재 요소 자체가 ol일 수도 있으므로 구분
        if element.name == "ol":
            lists = [element]
        else:
            lists = element.find_all("ol")

        # 발견한 각 목록의 직접적인 li 항목만 추출
        for ordered_list in lists:

            for li in ordered_list.find_all("li", recursive=False):

                # 서류명과 설명을 함께 보존
                document_text = li.get_text(" ", strip=True)

                if document_text:
                    required_documents.append(document_text)


# 3. 추출 결과 출력
for index, document in enumerate(required_documents, start=1):
    print(f"\n{index}. {document}")


print("\n추출한 목록 항목 수:", len(required_documents))


# 11. 해당자만 제출해야 하는 추가자료 추출하기

print("\n===== 해당자 추가 제출자료 =====")

# 1. '해당자만 제출해야 할 자료' 제목 찾기
conditional_heading = None

for heading in soup.find_all("h1"):

    title = heading.get_text(" ", strip=True)

    if "해당자만 제출해야 할 자료" in title:
        conditional_heading = heading
        break


# 2. 조건부 제출자료를 저장할 리스트
conditional_documents = []

if conditional_heading is None:
    print("조건부 제출자료 제목을 찾지 못했습니다.")

else:
    # 해당 제목 다음에 나오는 HTML 요소를 탐색
    for element in conditional_heading.next_siblings:

        # HTML 태그가 아닌 문자열은 건너뛰기
        if not isinstance(element, Tag):
            continue

        # 다음 h1 제목이 나오면 섹션 종료
        if element.name == "h1":
            break

        # ol 태그가 직접 나오거나 내부에 포함된 경우 처리
        if element.name == "ol":
            lists = [element]
        else:
            lists = element.find_all("ol")

        # 순서 있는 목록에서 직접적인 li만 추출
        for ordered_list in lists:

            for li in ordered_list.find_all(
                "li",
                recursive=False
            ):

                # 서류명과 주의사항을 함께 추출
                document_text = li.get_text(" ", strip=True)

                if document_text:
                    conditional_documents.append(document_text)


# 3. 추출한 목록 출력
for index, document in enumerate(
    conditional_documents,
    start=1
):
    print(f"\n{index}. {document}")


# 4. 추출 개수 확인
print(
    "\n조건부 제출자료 항목 수:",
    len(conditional_documents)
)

# 12. 추출한 제출자료를 JSON 파일로 저장하기

import json
from datetime import datetime, timezone


# 1. 실제 조건부 서류와 주의사항을 구분
# 현재 공식 HTML에서 확인한 순서를 기준으로 분리
# 앞의 2개는 서류, 마지막 1개는 주의사항
if len(conditional_documents) != 3:
    raise ValueError(
        "조건부 항목 수가 예상과 다릅니다. "
        "공식 HTML 구조를 다시 확인하세요."
    )

conditional_required = conditional_documents[:2]
submission_notes = conditional_documents[2:]


# 2. 저장할 딕셔너리 구성
documents_data = {
    "program_id": "jp_working_holiday",
    "target_nationality": "KR",

    "source": {
        "official_agency": "Embassy of Japan in Korea",
        "source_title": "Working Holiday 사증 안내(제출자료 안내)",
        "source_url": (
            "https://www.kr.emb-japan.go.jp/"
            "itpr_ko/visa_working_documents.html"
        ),

        # HTML에 표시된 날짜
        "page_display_date": "2025-11-04",

        # 데이터를 추출한 시각(UTC)
        "extracted_at": datetime.now(timezone.utc).isoformat()
    },

    # 제출서류 원문을 순서대로 보존
    "required_documents": required_documents,

    # 특정 조건에 해당할 때 제출하는 자료
    "conditional_documents": conditional_required,

    # 제출 시 주의사항
    "submission_notes": submission_notes,

    # 아직 조건별 구조화를 완료하지 않은 상태
    "validation_status": "needs_structuring"
}


# 3. JSON 파일 저장 경로
OUTPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "japan_working_holiday_documents.json"
)


# 4. UTF-8 형식으로 저장
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(
        documents_data,
        f,
        ensure_ascii=False,
        indent=2
    )


# 5. 저장 결과 확인
print("\n===== 제출서류 JSON 저장 결과 =====")

print("파일 존재:", OUTPUT_PATH.exists())
print("필수자료 수:", len(required_documents))
print("조건부 자료 수:", len(conditional_required))
print("주의사항 수:", len(submission_notes))
print("저장 경로:", OUTPUT_PATH)