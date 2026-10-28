"""
frontend/pages/programs.py
프로그램·지원제도 찾기 — 와이어프레임 image7 기준
"""
import streamlit as st
from components.header import render_header
from components.program_card import render_program_card
from utils.api import search_programs

TABS = ["전체", "프로그램", "지원제도"]
COUNTRIES = [
    ("전체", ""),
    ("독일", "🇩🇪"),
    ("일본", "🇯🇵"),
    ("호주", "🇦🇺"),
    ("미국", "🇺🇸"),
    ("캐나다", "🇨🇦"),
]
PURPOSES = ["전체", "취업", "유학·교환학생", "워킹홀리데이"]

@st.cache_data(ttl=60)
def _get_programs(tab, country, purpose, keyword):
    return search_programs({"tab": tab, "country": country, "purpose": purpose, "keyword": keyword})

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
    render_header(right_label="프로그램·지원제도 찾기")

    st.markdown(
        "<span style='font-size:0.65rem;font-weight:700;letter-spacing:0.15em;color:#aaa;'>"
        "● EXPLORE YOUR POSSIBILITIES</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<h2 style='font-size:1.3rem;font-weight:700;margin:0.2rem 0 1rem;color:#1a1a1a;'>"
        "프로그램·지원제도 찾기</h2>",
        unsafe_allow_html=True,
    )

    query = st.text_input(
        "",
        placeholder="🔍  국가, 프로그램명, 목적 등으로 검색",
        label_visibility="collapsed",
        key="prog_search",
    )

    st.markdown("<div style='margin-top:0.75rem;'></div>", unsafe_allow_html=True)

    # 탭 + 필터 초기화
    active_tab = st.session_state.get("prog_tab", "전체")
    tab_cols = st.columns(len(TABS) + 1)
    for col, tab in zip(tab_cols[:len(TABS)], TABS):
        with col:
            is_active = tab == active_tab
            if st.button(
                tab,
                key=f"tab_{tab}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state["prog_tab"] = tab
                st.rerun()
    with tab_cols[-1]:
        if st.button("필터 초기화", key="filter_reset", use_container_width=True):
            st.session_state["prog_tab"] = "전체"
            st.session_state["prog_country"] = "전체"
            st.session_state["prog_purpose"] = "전체"
            st.rerun()

    st.markdown(
        "<p style='font-size:0.8rem;color:#888;margin:0.5rem 0 1rem;'>"
        "국가, 비자 종류, 지원 목적으로 나에게 맞는 프로그램을 찾아보세요.</p>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<hr style='margin:0.25rem 0 0.75rem;border:none;border-top:1px solid #f0f0f0;'>",
        unsafe_allow_html=True,
    )

    # 국가 필터
    st.markdown(
        "<div style='font-size:0.75rem;color:#aaa;margin-bottom:0.3rem;'>국가</div>",
        unsafe_allow_html=True,
    )
    active_country = st.session_state.get("prog_country", "전체")
    country_cols = st.columns(len(COUNTRIES))
    for col, (c_name, c_flag) in zip(country_cols, COUNTRIES):
        with col:
            label = f"{c_flag} {c_name}".strip() if c_flag else c_name
            is_active = c_name == active_country
            if st.button(
                label,
                key=f"country_{c_name}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state["prog_country"] = c_name
                st.rerun()

    st.markdown("<div style='margin-top:0.5rem;'></div>", unsafe_allow_html=True)

    # 목적 필터
    st.markdown(
        "<div style='font-size:0.75rem;color:#aaa;margin-bottom:0.3rem;'>목적</div>",
        unsafe_allow_html=True,
    )
    active_purpose = st.session_state.get("prog_purpose", "전체")
    purpose_cols = st.columns(len(PURPOSES))
    for col, p in zip(purpose_cols, PURPOSES):
        with col:
            is_active = p == active_purpose
            if st.button(
                p,
                key=f"purpose_{p}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state["prog_purpose"] = p
                st.rerun()

    st.markdown(
        "<hr style='margin:0.75rem 0;border:none;border-top:1px solid #f0f0f0;'>",
        unsafe_allow_html=True,
    )

    # 결과
    filters = {
        "tab": active_tab,
        "country": active_country,
        "purpose": active_purpose,
        "keyword": query.strip() if query else "",
    }
    programs = _get_programs(active_tab, active_country, active_purpose, query.strip() if query else "")

    if programs:
        prog_count = sum(1 for p in programs if p.get("type") == "프로그램")
        sup_count = sum(1 for p in programs if p.get("type") == "지원제도")

        # 이전 렌더의 비교 체크박스 state
        compared = [
            p for p in programs
            if st.session_state.get(f"chk_compare_{p.get('id', p.get('name', ''))}", False)
        ]

        count_col, compare_col = st.columns([4, 1])
        with count_col:
            st.markdown(
                f"<div style='font-size:0.78rem;color:#aaa;margin-bottom:0.75rem;'>"
                f"총 {len(programs)}개 &nbsp;·&nbsp; 프로그램 {prog_count} &nbsp;·&nbsp; 지원제도 {sup_count}</div>",
                unsafe_allow_html=True,
            )
        with compare_col:
            compare_count = len(compared)
            if st.button(
                f"비교하기 ({compare_count})" if compare_count >= 2 else "비교하기",
                key="do_compare",
                use_container_width=True,
                type="primary" if compare_count >= 2 else "secondary",
                disabled=(compare_count < 2),
            ):
                st.session_state["show_compare_panel"] = not st.session_state.get(
                    "show_compare_panel", False
                )

        # 비교 패널
        if st.session_state.get("show_compare_panel") and len(compared) >= 2:
            st.markdown(
                "<div style='background:#f8f8f8;border-radius:12px;padding:1rem;margin-bottom:1rem;'>",
                unsafe_allow_html=True,
            )
            panel_cols = st.columns(len(compared))
            for col, cp in zip(panel_cols, compared):
                with col:
                    st.markdown(
                        f"<div style='font-size:0.7rem;color:#888;margin-bottom:0.2rem;'>"
                        f"{cp.get('type','')} &nbsp;·&nbsp; {cp.get('country','')}</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<div style='font-size:0.9rem;font-weight:700;margin-bottom:0.4rem;'>"
                        f"{cp.get('country_emoji','')} {cp.get('name','')}</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<div style='font-size:0.8rem;color:#555;'>{cp.get('description','')}</div>",
                        unsafe_allow_html=True,
                    )
            close_col, _ = st.columns([1, 4])
            with close_col:
                if st.button("닫기", key="close_compare"):
                    st.session_state["show_compare_panel"] = False
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        for prog in programs:
            render_program_card(prog, show_compare=True)

    else:
        st.markdown(
            """
            <div style="text-align:center;padding:3rem 0;color:#aaa;">
                <div style="font-size:1.5rem;margin-bottom:0.5rem;">🔍</div>
                <div style="font-size:0.9rem;">조건에 맞는 프로그램이 없어요.</div>
                <div style="font-size:0.8rem;margin-top:0.3rem;">필터를 조정해 보세요.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )