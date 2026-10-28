"""
frontend/pages/programs.py
프로그램·지원제도 찾기 화면
"""
import streamlit as st
from components.header import render_header
from components.sidebar import render_inner_sidebar
from components.program_card import render_program_card
from utils.session import PAGE_PROGRAMS
from utils.api import search_programs

TABS = ["전체", "프로그램", "지원제도"]
COUNTRIES = ["전체", "독일", "일본", "호주", "미국", "캐나다"]
PURPOSES = ["전체", "취업", "유학·교환학생", "워킹홀리데이"]


def render():
    render_header(right_label="프로그램·지원제도 찾기")
    render_inner_sidebar(PAGE_PROGRAMS)

    st.markdown(
        "<h2 style='font-size:1.1rem; font-weight:700; margin:0 0 1rem;'>프로그램·지원제도 찾기</h2>",
        unsafe_allow_html=True,
    )

    # 검색창
    query = st.text_input(
        "",
        placeholder="🔍  국가, 프로그램명, 목적 등으로 검색",
        label_visibility="collapsed",
        key="prog_search",
    )

    st.markdown("<div style='margin-top:0.75rem;'></div>", unsafe_allow_html=True)

    # 탭 (전체 / 프로그램 / 지원제도)
    active_tab = st.session_state.get("prog_tab", "전체")
    tab_cols = st.columns(len(TABS))
    for col, tab in zip(tab_cols, TABS):
        with col:
            is_active = tab == active_tab
            label = f"**{tab}**" if is_active else tab
            if st.button(
                label,
                key=f"tab_{tab}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state["prog_tab"] = tab
                st.rerun()

    st.markdown(
        "<hr style='margin:0.75rem 0; border:none; border-top:1px solid #f0f0f0;'>",
        unsafe_allow_html=True,
    )

    # 국가 필터
    st.markdown(
        "<div style='font-size:0.75rem; color:#aaa; margin-bottom:0.3rem;'>국가</div>",
        unsafe_allow_html=True,
    )
    active_country = st.session_state.get("prog_country", "전체")
    country_cols = st.columns(len(COUNTRIES))
    for col, c in zip(country_cols, COUNTRIES):
        with col:
            is_active = c == active_country
            if st.button(
                c,
                key=f"country_{c}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state["prog_country"] = c
                st.rerun()

    st.markdown("<div style='margin-top:0.5rem;'></div>", unsafe_allow_html=True)

    # 목적 필터
    st.markdown(
        "<div style='font-size:0.75rem; color:#aaa; margin-bottom:0.3rem;'>목적</div>",
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
        "<hr style='margin:0.75rem 0; border:none; border-top:1px solid #f0f0f0;'>",
        unsafe_allow_html=True,
    )

    # 결과 목록
    filters = {
        "type": active_tab if active_tab != "전체" else None,
        "country": active_country if active_country != "전체" else None,
        "purpose": active_purpose if active_purpose != "전체" else None,
        "query": query.strip() if query.strip() else None,
    }

    programs = search_programs(filters)

    if programs:
        st.markdown(
            f"<div style='font-size:0.78rem; color:#aaa; margin-bottom:0.75rem;'>"
            f"총 {len(programs)}개의 결과</div>",
            unsafe_allow_html=True,
        )
        for prog in programs:
            render_program_card(prog, show_compare=False)
    else:
        st.markdown(
            """
            <div style="text-align:center; padding:3rem 0; color:#aaa;">
                <div style="font-size:1.5rem; margin-bottom:0.5rem;">🔍</div>
                <div style="font-size:0.9rem;">조건에 맞는 프로그램이 없어요.</div>
                <div style="font-size:0.8rem; margin-top:0.3rem;">필터를 조정해 보세요.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
