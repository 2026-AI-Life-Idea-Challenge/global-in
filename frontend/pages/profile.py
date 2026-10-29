"""
frontend/pages/profile.py
내 프로필 화면
"""
import streamlit as st
from components.header import render_header
from components.sidebar import render_inner_sidebar
from utils.session import (
    go_to, get_profile, save_profile,
    PAGE_CHAT, PAGE_PROFILE
)


NATIONALITY_OPTIONS = ["한국", "일본", "미국", "중국", "기타"]
EDUCATION_OPTIONS = ["고등학교 졸업", "전문대 재학/졸업", "대학교 재학", "대학교 졸업", "대학원 재학/졸업"]
ENROLLMENT_OPTIONS = ["재학", "휴학", "졸업", "졸업예정", "해당없음"]
CAREER_FIELD_OPTIONS = ["IT/개발", "디자인", "마케팅/기획", "영업/영어", "연구/학술", "제조/생산", "의료/보건", "교육", "금융/회계", "기타"]
CAREER_DURATION_OPTIONS = ["경력 없음", "1년 미만", "1~3년", "3~5년", "5년 이상"]
LANGUAGE_OPTIONS = ["한국어", "영어", "일본어", "독일어", "기타"]
EXAM_OPTIONS = ["IELTS", "TOEFL", "JLPT", "DELF", "TestDaF", "없음"]

COUNTRY_FLAGS = {
    "일본": "🇯🇵",
    "호주": "🇦🇺",
    "미국": "🇺🇸",
    "독일": "🇩🇪",
    "캐나다": "🇨🇦",
}
PURPOSE_OPTIONS = ["취업", "유학", "워킹홀리데이·교류", "미정"]


def render():
    st.markdown("""
    <style>
    [data-testid="stToolbar"],[data-testid="stDecoration"],footer,#MainMenu { display:none !important; }
    </style>
    """, unsafe_allow_html=True)
    render_header(right_label="내 프로필")

    profile = get_profile()

    st.markdown(
        "<h2 style='font-size:1.2rem; font-weight:700; margin:0 0 1.5rem;'>내 프로필</h2>",
        unsafe_allow_html=True,
    )

    # ── 기본 정보 ──────────────────────────────────────────────
    _section_title("기본 정보")

    col1, col2 = st.columns(2)
    with col1:
        nationality = st.selectbox(
            "국적 *",
            NATIONALITY_OPTIONS,
            index=_idx(NATIONALITY_OPTIONS, profile.get("nationality")),
            key="p_nationality",
        )
    with col2:
        age_input = st.text_input(
            "만 나이 *",
            value=profile.get("age", ""),
            placeholder="예: 26",
            key="p_age",
        )

    current_country = st.text_input(
        "현재 거주 국가 *",
        value=profile.get("current_country", ""),
        placeholder="예: 대한민국",
        key="p_current_country",
    )

    # ── 학력 ───────────────────────────────────────────────────
    _section_title("학력")

    col1, col2 = st.columns(2)
    with col1:
        education = st.selectbox(
            "최종 학력",
            EDUCATION_OPTIONS,
            index=_idx(EDUCATION_OPTIONS, profile.get("education")),
            key="p_education",
        )
    with col2:
        enrollment = st.selectbox(
            "학적 상태",
            ENROLLMENT_OPTIONS,
            index=_idx(ENROLLMENT_OPTIONS, profile.get("enrollment_status")),
            key="p_enrollment",
        )

    major = st.text_input(
        "전공",
        value=profile.get("major", ""),
        placeholder="예: 컴퓨터공학",
        key="p_major",
    )

    # ── 경력 ───────────────────────────────────────────────────
    _section_title("경력")

    col1, col2 = st.columns(2)
    with col1:
        career_field = st.selectbox(
            "직무·경력 분야",
            CAREER_FIELD_OPTIONS,
            index=_idx(CAREER_FIELD_OPTIONS, profile.get("career_field")),
            key="p_career_field",
        )
    with col2:
        career_duration = st.selectbox(
            "경력 기간",
            CAREER_DURATION_OPTIONS,
            index=_idx(CAREER_DURATION_OPTIONS, profile.get("career_duration")),
            key="p_career_duration",
        )

        # ── 언어 ───────────────────────────────────────────────────
    _section_title("언어")

    languages = st.multiselect(
    "사용 언어",
    LANGUAGE_OPTIONS,
    default=[
        lang for lang in profile.get("languages", [])
        if lang in LANGUAGE_OPTIONS
    ],
    key="p_languages",
    )

    col1, col2 = st.columns(2)
    with col1:
        exam = st.selectbox(
            "어학 시험·자격",
            EXAM_OPTIONS,
            index=_idx(EXAM_OPTIONS, profile.get("language_exam")),
            key="p_exam",
        )
    with col2:
        exam_score = st.text_input(
            "점수·등급",
            value=profile.get("language_exam_score", ""),
            placeholder="예: 7.0 / N2",
            key="p_exam_score",
        )

    # ── 관심 국가 ──────────────────────────────────────────────
    _section_title("관심 국가")

    current_countries = profile.get("target_countries", [])
    selected_countries = []
    cols = st.columns(len(COUNTRY_FLAGS) + 1)
    for col, (country, flag) in zip(cols, COUNTRY_FLAGS.items()):
        with col:
            checked = st.checkbox(
                f"{flag}\n{country}",
                value=country in current_countries,
                key=f"p_country_{country}",
            )
            if checked:
                selected_countries.append(country)
    with cols[-1]:
        undecided_country = st.checkbox(
            "🌐\n미정",
            value=not current_countries,
            key="p_country_undecided",
        )

    # ── 진출 목적 ──────────────────────────────────────────────
    _section_title("진출 목적")

    current_purpose = profile.get("purpose", "미정")
    purpose_cols = st.columns(len(PURPOSE_OPTIONS))
    selected_purpose = current_purpose
    for col, p in zip(purpose_cols, PURPOSE_OPTIONS):
        with col:
            if st.button(
                p,
                key=f"p_purpose_{p}",
                use_container_width=True,
                type="primary" if st.session_state.get("_purpose_sel", current_purpose) == p else "secondary",
            ):
                st.session_state["_purpose_sel"] = p
                selected_purpose = p

    if "_purpose_sel" in st.session_state:
        selected_purpose = st.session_state["_purpose_sel"]

    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)

    # ── 저장 버튼 ─────────────────────────────────────────────
    col_save, col_chat = st.columns(2)

    with col_save:
        if st.button("프로필 저장하기", key="p_save", use_container_width=True):
            _save(
                nationality, age_input, current_country,
                education, enrollment, major,
                career_field, career_duration,
                languages, exam, exam_score,
                selected_countries, selected_purpose,
            )
            st.success("프로필이 저장되었어요!")

    with col_chat:
        if st.button(
            "이 정보로 상담하기  →",
            key="p_chat",
            use_container_width=True,
            type="primary",
        ):
            _save(
                nationality, age_input, current_country,
                education, enrollment, major,
                career_field, career_duration,
                languages, exam, exam_score,
                selected_countries, selected_purpose,
            )
            go_to(PAGE_CHAT)


# ─── helpers ──────────────────────────────────────────────────────────────────

def _section_title(text: str):
    st.markdown(
        f"""
        <div style="font-size:0.8rem; font-weight:600; letter-spacing:0.04em;
             color:#888; margin:1.4rem 0 0.6rem; text-transform:uppercase;">
            {text}
        </div>
        <hr style="margin:0 0 0.75rem; border:none; border-top:1px solid #f0f0f0;">
        """,
        unsafe_allow_html=True,
    )


def _idx(options: list, value) -> int:
    try:
        return options.index(value) if value in options else 0
    except Exception:
        return 0


def _save(
    nationality, age_input, current_country,
    education, enrollment, major,
    career_field, career_duration,
    languages, exam, exam_score,
    target_countries, purpose,
):
    save_profile({
        "nationality": nationality,
        "age": age_input,
        "current_country": current_country,
        "education": education,
        "enrollment_status": enrollment,
        "major": major,
        "career_field": career_field,
        "career_duration": career_duration,
        "languages": languages,
        "language_exam": exam,
        "language_exam_score": exam_score,
        "target_countries": target_countries,
        "purpose": purpose,
    })
