"""
frontend/app.py
Global-In Streamlit 앱 진입점
"""
import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from components.header import render_header
from components.sidebar import render_inner_sidebar
from utils.session import (
    init_session,
    PAGE_HOME, PAGE_CHAT, PAGE_PROGRAMS,
    PAGE_PREPARATION, PAGE_PROFILE,
)

st.set_page_config(
    page_title="Global-In",
    page_icon="⊙",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── 전역 스타일 ────────────────────────────────────────────
_style_path = os.path.join(os.path.dirname(__file__), "styles", "global.css")
if os.path.exists(_style_path):
    with open(_style_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.markdown("""
<style>
[data-testid="stToolbar"],[data-testid="stDecoration"],footer,#MainMenu { display:none !important; }
[data-testid="stSidebar"], [data-testid="stSidebarNav"],
button[kind="header"], [data-testid="collapsedControl"] { display:none !important; }
[data-testid="stMainBlockContainer"] {
    padding-top: 1rem !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    max-width: 100% !important;
}
/* 헤더 제외하고 두 번째 블록(columns)부터 좌우 패딩 */
[data-testid="stMainBlockContainer"] > div > div > div:nth-child(2) {
    padding-left: 2rem !important;
    padding-right: 2rem !important;
}
</style>
""", unsafe_allow_html=True)

# ── 세션 초기화 ────────────────────────────────────────────
init_session()

# ── 라우팅 ────────────────────────────────────────────────
page = st.session_state.get("page", PAGE_HOME)

PAGE_LABELS = {
    PAGE_CHAT:        "AI 상담",
    PAGE_PROGRAMS:    "프로그램·지원제도 찾기",
    PAGE_PREPARATION: "내 준비",
    PAGE_PROFILE:     "내 프로필",
}

if page == PAGE_HOME:
    from pages.home import render
    render()
else:
    # 헤더도 콘텐츠와 같은 너비로
    h_left, h_center, h_right = st.columns([1, 3.9, 1], gap="small")
    with h_center:
        render_header(right_label=PAGE_LABELS.get(page, ""))

    # 사이드바 + 콘텐츠
    sp_left, col_side, col_main, sp_right = st.columns([1, 0.9, 3, 1], gap="small")

    with col_side:
        render_inner_sidebar(page)

    with col_main:
        if page == PAGE_CHAT:
            from pages.chat import render
        elif page == PAGE_PROGRAMS:
            from pages.programs import render
        elif page == PAGE_PREPARATION:
            from pages.preparation import render
        elif page == PAGE_PROFILE:
            from pages.profile import render
        else:
            from pages.home import render
        render()