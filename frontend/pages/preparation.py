"""
frontend/pages/preparation.py
내 준비 화면 — 와이어프레임 image8/9 기준
"""
import streamlit as st
from components.header import render_header
from components.checklist_item import render_checklist_item
from utils.session import PAGE_PROGRAMS, PAGE_CHAT, go_to

CHECKLIST_FILTERS = ["공식 준비 항목", "AI 추천", "내가 추가"]

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
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"]             { display:block !important; }
        [data-testid="stSidebarCollapsedControl"] { display:block !important; }
        [data-testid="stToolbar"],[data-testid="stDecoration"],footer,#MainMenu
                                               { display:none !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    render_header(right_label="내 계획")

    saved = list(st.session_state.get("saved_programs", {}).values())

    # saved가 없으면 checklist 초기화 후 빈 화면
    if not saved:
        st.session_state["preparation_items"] = []
        st.session_state["selected_prog_id"] = None
        _render_empty_state()
        return

    items = st.session_state.get("preparation_items") or []
    if not items:
        items = SAMPLE_CHECKLIST
        st.session_state["preparation_items"] = items

    checked_count = sum(1 for i in items if i.get("checked"))
    total_count = len(items)

    st.markdown(
        "<span style='font-size:0.65rem;font-weight:700;letter-spacing:0.15em;color:#aaa;'>"
        "● MY PREPARATION</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<h2 style='font-size:1.3rem;font-weight:700;margin:0.2rem 0 1rem;color:#1a1a1a;'>"
        "내 준비</h2>",
        unsafe_allow_html=True,
    )

    # 관심 프로그램 — 클릭 가능한 카드
    st.markdown(
        "<div style='font-size:0.78rem;font-weight:600;color:#1a1a1a;margin-bottom:0.5rem;'>"
        f"관심 프로그램 <span style='color:#aaa;font-weight:400;'>({len(saved)})</span></div>",
        unsafe_allow_html=True,
    )

    selected_id = st.session_state.get("selected_prog_id")
    prog_cols = st.columns(min(len(saved), 3))
    for i, prog in enumerate(saved[:3]):
        p_id = prog.get("id", prog.get("name", str(i)))
        is_sel = selected_id == p_id
        with prog_cols[i]:
            # 카드 스타일 배경
            border_color = "#1a1a1a" if is_sel else "#e8e8e8"
            bg_color = "#f8f8f8" if is_sel else "#fff"
            st.markdown(
                f"""<div style='border:1.5px solid {border_color};border-radius:12px;
                     padding:0.75rem;background:{bg_color};margin-bottom:0.3rem;'>
                    <div style='font-size:0.68rem;color:#888;'>
                        {prog.get('type','')} · {prog.get('purpose','')}</div>
                    <div style='font-size:0.82rem;font-weight:700;color:#1a1a1a;margin:0.15rem 0;'>
                        {prog.get('country_emoji','')} {prog.get('name','')}</div>
                    <div style='font-size:0.68rem;color:#aaa;'>{prog.get('country','')}</div>
                </div>""",
                unsafe_allow_html=True,
            )
            btn_label = "✓ 선택됨" if is_sel else "선택하기"
            if st.button(btn_label, key=f"sel_prog_{p_id}", use_container_width=True,
                         type="primary" if is_sel else "secondary"):
                st.session_state["selected_prog_id"] = None if is_sel else p_id
                st.rerun()

    if len(saved) > 3:
        st.markdown(
            f"<div style='font-size:0.75rem;color:#aaa;margin-top:0.25rem;'>외 {len(saved)-3}개 더</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<hr style='border:none;border-top:1px solid #f0f0f0;margin:0.75rem 0 1rem;'>",
                unsafe_allow_html=True)

    # 선택된 프로그램 표시
    if selected_id:
        sel_prog = next((p for p in saved if p.get("id", p.get("name")) == selected_id), None)
        if sel_prog:
            st.markdown(
                f"<div style='font-size:0.78rem;color:#555;margin-bottom:0.5rem;'>"
                f"📌 <b>{sel_prog.get('name','')}</b> 기준 체크리스트</div>",
                unsafe_allow_html=True,
            )

    # 진행 요약
    pct = int(checked_count / total_count * 100) if total_count else 0
    st.markdown(
        f"""
        <div style='margin-bottom:0.75rem;'>
            <div style='font-size:0.9rem;font-weight:700;color:#1a1a1a;'>체크리스트</div>
            <div style='font-size:0.75rem;color:#888;margin-top:0.15rem;'>
                {total_count}개 항목 · {checked_count}개 완료</div>
        </div>
        <div style='background:#f0f0f0;border-radius:999px;height:5px;margin-bottom:1rem;'>
            <div style='background:#1a1a1a;border-radius:999px;height:5px;width:{pct}%;'></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 필터 탭
    active_filter = st.session_state.get("prep_filter", None)
    filter_cols = st.columns(len(CHECKLIST_FILTERS))
    for col, f in zip(filter_cols, CHECKLIST_FILTERS):
        with col:
            is_active = f == active_filter
            if st.button(f, key=f"prep_filter_{f}", use_container_width=True,
                         type="primary" if is_active else "secondary"):
                st.session_state["prep_filter"] = None if is_active else f
                st.rerun()

    st.markdown("<div style='margin-top:0.75rem;'></div>", unsafe_allow_html=True)

    filtered = [i for i in items if not active_filter or active_filter in i.get("tags", [])]
    _render_section("01", "신청 전 준비", filtered[:3], start_idx=0)
    _render_section("02", "신청 준비", filtered[3:], start_idx=3)

    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
    if st.button("💬  AI에게 준비 방법 물어보기", key="prep_ask_ai",
                 use_container_width=True, type="primary"):
        go_to(PAGE_CHAT)


def _render_section(num: str, title: str, section_items: list, start_idx: int = 0):
    if not section_items:
        return
    st.markdown(
        f"""
        <div style='display:flex;justify-content:space-between;align-items:center;
             margin-bottom:0.5rem;margin-top:0.25rem;'>
            <div style='font-size:0.82rem;font-weight:700;color:#1a1a1a;'>
                <span style='color:#aaa;margin-right:0.4rem;font-weight:400;'>{num}</span>
                {title}
            </div>
            <div style='font-size:0.72rem;color:#aaa;'>
                {sum(1 for i in section_items if i.get('checked'))}/{len(section_items)} 완료
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    for idx, item in enumerate(section_items):
        render_checklist_item(item, start_idx + idx)
    st.markdown("<div style='margin-bottom:0.75rem;'></div>", unsafe_allow_html=True)


def _render_empty_state():
    st.markdown(
        "<span style='font-size:0.65rem;font-weight:700;letter-spacing:0.15em;color:#aaa;'>"
        "● MY PREPARATION</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div style='display:flex;flex-direction:column;align-items:center;
             justify-content:center;padding:3rem 1rem;text-align:center;'>
            <div style='font-size:2.5rem;margin-bottom:1rem;'>📋</div>
            <div style='font-size:1rem;font-weight:700;color:#1a1a1a;margin-bottom:0.4rem;'>
                아직 준비 중인 항목이 없어요.
            </div>
            <div style='font-size:0.82rem;color:#aaa;line-height:1.6;margin-bottom:2rem;'>
                프로그램을 찾거나 AI와 상담하면<br>나만의 체크리스트를 만들 수 있어요.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("프로그램 찾아보기", key="prep_empty_prog",
                     use_container_width=True, type="primary"):
            go_to(PAGE_PROGRAMS)
    with col2:
        if st.button("AI 상담하기", key="prep_empty_chat", use_container_width=True):
            go_to(PAGE_CHAT)