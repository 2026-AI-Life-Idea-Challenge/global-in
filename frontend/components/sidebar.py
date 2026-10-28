"""
frontend/components/sidebar.py
서브페이지 공통 사이드바 (AI 상담 / 프로그램찾기 / 내 준비)
"""
import streamlit as st
from utils.session import (
    go_to, new_chat_session,
    PAGE_CHAT, PAGE_PROGRAMS, PAGE_PREPARATION, PAGE_PROFILE,
)


def render_inner_sidebar(active_page: str):
    """
    AI 상담·프로그램찾기·내 준비 화면의 왼쪽 사이드바.
    active_page: 현재 활성 탭 식별자
    """
    with st.sidebar:
        # 돌아보기 / 상단 구분
        st.markdown(
            "<div style='font-size:0.72rem; color:#aaa; font-weight:500;"
            " letter-spacing:0.05em; margin-bottom:0.5rem;'>돌아보기</div>",
            unsafe_allow_html=True,
        )

        _nav_item("💬  AI 상담", PAGE_CHAT, active_page)
        _nav_item("⊙  프로그램·지원제도 찾기", PAGE_PROGRAMS, active_page)
        _nav_item("≡  내 준비", PAGE_PREPARATION, active_page)

        st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)

        # 내 프로필
        if st.button(
            "👤  내 프로필",
            key="sidebar_profile",
            use_container_width=True,
        ):
            go_to(PAGE_PROFILE)

        # AI 상담 전용 — 새 채팅 + 목록
        if active_page == PAGE_CHAT:
            _render_chat_list()


def _nav_item(label: str, target_page: str, active_page: str):
    is_active = target_page == active_page
    style = (
        "background:#f0f0f0; border-radius:8px; font-weight:600;"
        if is_active
        else ""
    )
    if st.button(
        label,
        key=f"nav_{target_page}",
        use_container_width=True,
        type="secondary",
    ):
        go_to(target_page)


def _render_chat_list():
    st.markdown("<hr style='margin:1rem 0; border:none; border-top:1px solid #f0f0f0;'>",
                unsafe_allow_html=True)

    if st.button("＋  새 채팅", key="new_chat_btn", use_container_width=True, type="primary"):
        new_chat_session()
        go_to(PAGE_CHAT)

    sessions = st.session_state.get("chat_sessions", [])
    if sessions:
        st.markdown(
            "<div style='font-size:0.72rem; color:#aaa; margin:0.75rem 0 0.4rem;'>채팅 목록</div>",
            unsafe_allow_html=True,
        )
        for s in reversed(sessions):
            is_current = s["id"] == st.session_state.get("current_chat_id")
            label = ("💬  " if is_current else "○  ") + s["title"]
            if st.button(label, key=f"chat_{s['id']}", use_container_width=True):
                st.session_state.current_chat_id = s["id"]
                st.rerun()
