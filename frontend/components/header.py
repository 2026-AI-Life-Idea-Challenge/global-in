"""
frontend/components/header.py
공통 헤더 컴포넌트
"""
import streamlit as st
from utils.session import go_to, PAGE_HOME


def render_header(right_label: str = "", show_nav: bool = False):
    """
    상단 헤더를 렌더링.
    right_label: 우측에 표시할 텍스트 (예: '● 맞춤 상담', '● 내 프로필')
    show_nav: 홈에서만 True — 서비스 소개 / 이용 방법 버튼 표시
    """
    left, right = st.columns([1, 1])

    with left:
        if st.button(
            "⊙  Global-In .",
            key="header_logo",
            help="홈으로",
        ):
            go_to(PAGE_HOME)

    with right:
        if right_label:
            st.markdown(
                f"""
                <div style="text-align:right; padding-top:0.6rem;
                     font-size:0.82rem; color:#555; font-weight:500;">
                    ● {right_label}
                </div>
                """,
                unsafe_allow_html=True,
            )
        if show_nav:
            c1, c2 = st.columns(2)
            with c1:
                st.button("서비스 소개", key="nav_intro", use_container_width=True)
            with c2:
                st.button("이용 방법", key="nav_howto", use_container_width=True)

    st.markdown(
        "<hr style='margin:0.5rem 0 1rem 0; border:none; border-top:1px solid #f0f0f0;'>",
        unsafe_allow_html=True,
    )
