"""
frontend/pages/home.py
홈화면 (랜딩 페이지)
"""
import streamlit as st
from components.header import render_header
from utils.session import go_to, PAGE_CHAT, PAGE_PROFILE


def render():
    render_header(show_nav=True)

    # Hero section
    st.markdown(
        """
        <div style="text-align:center; padding:3rem 1rem 2rem;">
            <div style="font-size:3.5rem; margin-bottom:1.5rem; line-height:1;">
                🇯🇵 🇦🇺 🇺🇸 🇩🇪 🇨🇦
            </div>
            <h1 style="font-size:1.8rem; font-weight:700; color:#1a1a1a;
                       margin:0 0 0.75rem; line-height:1.4;">
                해외에서의 시작,<br>내 조건에 맞게.
            </h1>
            <p style="font-size:1rem; color:#666; margin:0 0 2rem; line-height:1.6;">
                내 상황에 맞는 국가·비자·프로그램을<br>AI가 직접 찾아드립니다.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # CTA button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            "상담 시작하기  →",
            key="hero_cta",
            use_container_width=True,
            type="primary",
        ):
            go_to(PAGE_CHAT)

    st.markdown("<div style='margin-top:3rem;'></div>", unsafe_allow_html=True)

    # Feature cards
    c1, c2, c3 = st.columns(3)
    _feature_card(c1, "🔍", "맞춤 프로그램 탐색", "내 학력·경력·언어 조건으로 지원 가능한 비자와 프로그램을 자동으로 찾아드려요.")
    _feature_card(c2, "📋", "준비 체크리스트", "단계별 준비 항목과 공식 정보 링크를 한눈에 확인하세요.")
    _feature_card(c3, "💬", "AI 1:1 상담", "언제든지 궁금한 점을 물어보고 실시간으로 답변받으세요.")

    st.markdown("<div style='margin-top:3rem;'></div>", unsafe_allow_html=True)

    # HOW IT WORKS
    st.markdown(
        """
        <div style="text-align:center; font-size:0.72rem; font-weight:600;
             letter-spacing:0.12em; color:#888; margin-bottom:1.5rem;">
            HOW IT WORKS
        </div>
        """,
        unsafe_allow_html=True,
    )

    steps = [
        ("01", "프로필 입력", "국적·학력·경력·언어 등 기본 정보를 입력해요."),
        ("02", "AI 상담 시작", "원하는 나라와 목적을 AI에게 편하게 이야기해요."),
        ("03", "프로그램 추천", "조건에 맞는 비자·프로그램 목록을 받아봐요."),
        ("04", "준비 시작", "체크리스트를 따라 단계별로 준비를 진행해요."),
    ]
    cols = st.columns(4)
    for col, (num, title, desc) in zip(cols, steps):
        with col:
            st.markdown(
                f"""
                <div style="text-align:center; padding:1rem 0.5rem;">
                    <div style="font-size:1.4rem; font-weight:700; color:#1a1a1a;
                         margin-bottom:0.4rem;">{num}</div>
                    <div style="font-size:0.85rem; font-weight:600; color:#1a1a1a;
                         margin-bottom:0.4rem;">{title}</div>
                    <div style="font-size:0.78rem; color:#888; line-height:1.5;">{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)

    # Bottom CTA
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            "👤  내 프로필 먼저 설정하기",
            key="profile_cta",
            use_container_width=True,
        ):
            go_to(PAGE_PROFILE)


def _feature_card(col, icon: str, title: str, desc: str):
    with col:
        st.markdown(
            f"""
            <div style="background:#fff; border:1px solid #f0f0f0; border-radius:12px;
                 padding:1.25rem 1rem; height:100%; min-height:140px;">
                <div style="font-size:1.5rem; margin-bottom:0.6rem;">{icon}</div>
                <div style="font-size:0.88rem; font-weight:600; color:#1a1a1a;
                     margin-bottom:0.4rem;">{title}</div>
                <div style="font-size:0.78rem; color:#888; line-height:1.5;">{desc}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
