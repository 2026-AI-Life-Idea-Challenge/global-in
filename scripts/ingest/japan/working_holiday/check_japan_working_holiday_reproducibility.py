
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[4]


# 검사 대상별 구조화 스크립트, 결과 JSON, Raw 입력 파일 매핑
# 허용된 데이터셋만 선택할 수 있도록 명시적으로 관리한다.
DATASET_CONFIG = {
    "programme_overview": {
        "script": "structure_japan_working_holiday_programme_overview.py",
        "output": "japan_working_holiday_programme_overview_structured.json",
        "raw": "japan_working_holiday.html",
    },
    "useful_information": {
        # STEP 56-5에서 만든 구조화 스크립트
        "script": "structure_japan_working_holiday_useful_information.py",

        # 비교할 기존 서비스용 JSON
        "output": "japan_working_holiday_useful_information_structured.json",

        # 구조화에 사용한 공식 원문 Raw JSON
        "raw": "japan_working_holiday_useful_information.json",
    },
    "visa_validity": {
        # 일본 대사관 HTML에서 사증 유효기간 추출
        "script": "structure_japan_working_holiday_visa_validity.py",

        # 기존 구조화 데이터와 비교
        "output": "japan_working_holiday_visa_validity_structured.json",

        # 재생성에 필요한 공식 HTML
        "raw": "japan_working_holiday_embassy.html",
    },
    "accredited_agencies": {
        # 일본 대사관 지정 여행사 PDF 구조화
        "script": "structure_japan_working_holiday_accredited_agencies.py",

        # 기존 구조화 JSON과 비교
        "output": "japan_working_holiday_accredited_agencies_structured.json",

        # 공식 PDF 원본
        "raw": "japan_working_holiday_accredited_agencies.pdf",
    },
    "application": {
        # 일본 대사관 신청수속 Raw JSON 구조화
        "script": "structure_japan_working_holiday_application.py",

        # 비교할 기존 구조화 JSON
        "output": "japan_working_holiday_application_structured.json",

        # STEP 54에서 추출한 공식 원문 Raw JSON
        "raw": "japan_working_holiday_application.json",
    },
    "documents": {
        # 일본 워킹홀리데이 제출서류 Raw JSON 구조화
        "script": "structure_japan_working_holiday_documents.py",

        # 기존 최종 제출서류 JSON과 비교
        "output": "japan_working_holiday_documents_structured.json",

        # 대사관 제출서류 원문 Raw JSON
        "raw": "japan_working_holiday_documents.json",
    },
    "rules": {
        # 외무성과 대사관의 자격요건 Raw JSON을 함께 사용
        "script": "structure_japan_working_holiday.py",

        # 기존 11개 자격요건 데이터셋
        "output": "japan_working_holiday_rules.json",

        # 복수 입력 파일
        "raw_files": [
            "japan_working_holiday_eligibility.json",
            "japan_working_holiday_embassy_eligibility.json",
        ],
    },
    "work_conditions": {
        # 취업 제한 Raw JSON 구조화
        "script": "structure_japan_working_holiday_work_conditions.py",
        "output": "japan_working_holiday_work_conditions_structured.json",
        "raw": "japan_working_holiday_work_conditions.json",
    },
    "post_entry": {
        # 입국 후 절차 구조화 스크립트
        "script": "structure_japan_working_holiday_post_entry.py",

        # 최종 비교 대상
        "output": "japan_working_holiday_post_entry_structured.json",

        # 이미 추출된 공식 원문
        "raw": "japan_working_holiday_post_entry.json",

        # 구조화 후 공식 근거 보강
        "postprocess": "enrich_japan_working_holiday_post_entry.py",
    },
}

# CMD에서 검사할 데이터셋을 인자로 받는다.
if len(sys.argv) != 2 or sys.argv[1] not in DATASET_CONFIG:
    raise SystemExit(
        "사용법: python check_japan_working_holiday_reproducibility.py "
        "[programme_overview|work_conditions]"
    )

selected = DATASET_CONFIG[sys.argv[1]]

SCRIPT_NAME = selected["script"]
DATA_NAME = selected["output"]
# 기존 단일 입력 데이터셋과 신규 복수 입력 데이터셋 모두 지원
RAW_NAMES = selected.get("raw_files", [selected["raw"]]) if "raw_files" not in selected else selected["raw_files"]


def sha256(path: Path) -> str:
    """파일 내용의 SHA-256 해시를 계산한다."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(obj):
    """실행 시각처럼 매번 달라지는 메타데이터만 제외한다."""
    if isinstance(obj, dict):
        return {
            key: normalize(value)
            for key, value in obj.items()
            if key != "extracted_at"
        }

    if isinstance(obj, list):
        return [normalize(value) for value in obj]

    return obj


def main():
    baseline_path = (
        PROJECT_ROOT
        / "data/raw/japan/working_holiday/japan_working_holiday_hash_baseline.json"
    )

    original_path = PROJECT_ROOT / "data/processed/japan/working_holiday" / DATA_NAME
    script_path = PROJECT_ROOT / "scripts/ingest/japan/working_holiday" / SCRIPT_NAME

    baseline = json.loads(
        baseline_path.read_text(encoding="utf-8")
    )

    # 재생성 전에 기존 파일이 기준값과 일치하는지 확인
    if sha256(original_path) != baseline[DATA_NAME]:
        raise ValueError("기존 JSON이 SHA-256 기준값과 다릅니다.")

    with tempfile.TemporaryDirectory() as temp:
        # 프로젝트와 분리된 임시 작업공간
        temp_root = Path(temp)

        temp_script = temp_root / "scripts/ingest/japan/working_holiday" / SCRIPT_NAME
        temp_output = temp_root / "data/processed/japan/working_holiday" / DATA_NAME

        # 임시 프로젝트에 구조화 스크립트 복사
        temp_script.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(script_path, temp_script)


        # 후처리 스크립트가 있으면 임시 폴더에 함께 복사
        postprocess_name = selected.get("postprocess")

        if postprocess_name:
            postprocess_source = (
                PROJECT_ROOT / "scripts/ingest/japan/working_holiday" / postprocess_name
            )
            postprocess_script = (
                temp_root / "scripts/ingest/japan/working_holiday" / postprocess_name
            )

            shutil.copy2(postprocess_source, postprocess_script)

        # Raw 입력 파일을 임시 폴더에 복사
        temp_raw_dir = temp_root / "data/raw/japan/working_holiday"
        temp_raw_dir.mkdir(parents=True, exist_ok=True)

        for raw_name in RAW_NAMES:
            source = PROJECT_ROOT / "data/raw/japan/working_holiday" / raw_name
            destination = temp_raw_dir / raw_name

            if not source.is_file():
                raise FileNotFoundError(source)

            shutil.copy2(source, destination)

        # 임시 폴더의 스크립트를 실행
        subprocess.run(
            [sys.executable, str(temp_script)],
            cwd=temp_root,
            check=True,
        )

        # 구조화가 끝난 다음 공식 근거 보강 실행
        if postprocess_name:
            subprocess.run(
                [sys.executable, str(postprocess_script)],
                cwd=temp_root,
                check=True,
            )

        if not temp_output.is_file():
            raise FileNotFoundError(
                "재생성된 임시 JSON을 찾을 수 없습니다."
            )

        original = json.loads(
            original_path.read_text(encoding="utf-8")
        )
        regenerated = json.loads(
            temp_output.read_text(encoding="utf-8")
        )

        # JSON 필드와 값 비교
        same = normalize(original) == normalize(regenerated)

    # 임시 폴더 삭제 후 기존 파일 불변 여부 재검증
    unchanged = sha256(original_path) == baseline[DATA_NAME]

    print("===== STEP 61-5 재현 가능성 검증 =====")
    print("대상:", DATA_NAME)
    print("기존 JSON과 재생성 JSON 일치:", same)
    print("기존 JSON 변경 없음:", unchanged)

    if not same:
        raise AssertionError("JSON 데이터 내용이 일치하지 않습니다.")

    if not unchanged:
        raise AssertionError("기존 JSON 파일이 변경됐습니다.")

    print("전체 검증: 성공")


if __name__ == "__main__":
    main()
