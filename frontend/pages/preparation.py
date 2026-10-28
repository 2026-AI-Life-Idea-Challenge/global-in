"""
frontend/pages/preparation.py
내 계획 화면 (구: 내 준비)
"""
import streamlit as st
from components.header import render_header
from components.sidebar import render_inner_sidebar
from components.checklist_item import render_checklist_item
from utils.session import PAGE_PREPARATION, go_to, PAGE_PROGRAMS, PAGE_CHAT


SAMPLE_CHECKLIST = [
    {
        "id": "chk_1",
        "title": "여권 유효기간 확인",
        "description": "워킹홀리데이 비자는 여권 유효기간이 1년 이상 남아 있어야 합니다.",
        "status": "done",
        "tags": ["공식 준비 항목"],
        "checked": True,
        "official_link": "https://www.mofa.go.kr",
        "official_source": "외교부",
    },
    {
        "id": "chk_2",
        "title": "영어 어학 성적 준비 (IELTS / TOEFL)",
        "description": "유학 비자는 영어 성적이 필수이며, 학교마다 요구 점수가 다릅니다.",
        "status": "in_progress",
        "tags": ["공식 준비 항목", "AI 추천"],
        "checked": False,
        "official_link": None,
        "official_source": None,
    },
    {
        "id": "chk_3",
        "title": "재정 보증 서류 준비",
        "description": "은행 잔고증명서 등 재정 능력 증빙이 필요합니다.",
        "status": "todo",
        "tags": ["AI 추천"],
        "checked": False,
        "official_link": None,
        "official_source": None,
    },
    {
        "id": "chk_4",
        "title": "건강 보험 확인",
        "description": "국가별로 여행자 보험 혹은 현지 의료보험 가입 요건이 다릅니다.",
        "status": "todo",
        "tags": ["공식 준비 항목"],
        "checked": False,
        "official_link": None,
        "official_source": None,
    },
    {
        "id": "chk_5",
        "title": "숙소 사전 예약",
        "description": "입국 시 주소지를 요구하는 국가가 있으니 미리 준비하세요.",
        "status": "todo",
        "tags": ["AI 추천"],
        "checked": False,
        "official_link": None,
        "official_source": None,
    },
]


def render():
    render_header(right_label="내 계획")
    render_inner_sidebar(PAGE_PREPARATION)

    # 준비 항목 로드
    items = st.session_state.get("preparation_items")
    if items is None:
        items = SAMPLE_CHECKLIST
        st.session_state["preparation_items"] = items

    checked_count = sum(1 for i in items if i.get("checked"))
    total_count = len(items)

    if total_count == 0:
        _render_empty_state()
        return

    # 상단 요약
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; gap:1rem; margin-bottom:1.25rem;">
            <div>
                <div style="font-size:1rem; font-weight:700; color:#1a1a1a;">내 계획</div>
                <div style="font-size:0.78rem; color:#888; margin-top:0.2rem;">
                    준비 중인 항목 {total_count}개 · {checked_count}개 완료
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 진행 바
    pct = int(checked_count / total_count * 100) if total_count else 0
    st.markdown(
        f"""
        <div style="background:#f0f0f0; border-radius:999px; height:6px; margin-bottom:1.5rem;">
            <div style="background:#1a1a1a; border-radius:999px; height:6px; width:{pct}%;
                 transition:width 0.3s;"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 체크리스트 섹션 헤더
    done_count = checked_count
    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center;
             margin-bottom:0.75rem;">
            <div style="font-size:0.82rem; font-weight:600; color:#1a1a1a;">
                신청 전 준비
            </div>
            <div style="font-size:0.75rem; color:#aaa;">
                {done_count}/{total_count} 완료
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 체크리스트 항목
    for idx, item in enumerate(items):
        render_checklist_item(item, idx)

    # AI 상담 버튼
    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
    if st.button(
        "💬  AI에게 준비 방법 물어보기",
        key="prep_ask_ai",
        use_container_width=True,
        type="primary",
    ):
        go_to(PAGE_CHAT)


def _render_empty_state():
    st.markdown(
        """
        <div style="text-align:center; padding:4rem 1rem;">
            <div style="font-size:2rem; margin-bottom:1rem;">📋</div>
            <div style="font-size:1rem; font-weight:600; color:#1a1a1a; margin-bottom:0.4rem;">
                아직 준비 중인 항목이 없어요.
            </div>
            <div style="font-size:0.85rem; color:#aaa; margin-bottom:2rem; line-height:1.6;">
                프로그램을 찾거나 AI와 상담하면<br>나만의 체크리스트를 만들 수 있어요.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("프로그램 찾아보기", key="prep_empty_prog", use_container_width=True):
            go_to(PAGE_PROGRAMS)
    with col2:
        if st.button("AI 상담하기", key="prep_empty_chat", use_container_width=True, type="primary"):
            go_to(PAGE_CHAT)
