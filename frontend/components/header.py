"""
frontend/components/header.py
글로벌 헤더 — 로고 클릭 시 홈 이동
"""
import streamlit as st
from utils.session import PAGE_HOME, PAGE_CHAT, PAGE_PROGRAMS, go_to


def render_header(right_label: str = "", show_nav: bool = False):
    cols = st.columns([3, 6, 3])

    with cols[0]:
        # 로고 버튼 → 홈 이동
        if st.button("⊙  Global-In .", key="header_logo", help="홈으로"):
            go_to(PAGE_HOME)

    with cols[1]:
        if show_nav:
            n1, n2 = st.columns(2)
            with n1:
                if st.button("서비스 소개", key="hdr_intro", use_container_width=True):
                    go_to(PAGE_HOME)
            with n2:
                if st.button("이용 방법", key="hdr_how", use_container_width=True):
                    go_to(PAGE_HOME)

    with cols[2]:
        if right_label:
            st.markdown(
                f"<div style='text-align:right; padding-top:0.4rem; "
                f"font-size:0.8rem; color:#888;'>● {right_label}</div>",
                unsafe_allow_html=True,
            )

    st.markdown(
        "<hr style='margin:0.25rem 0 0.75rem; border:none; border-top:1px solid #e8e8e8;'>",
        unsafe_allow_html=True,
    )
