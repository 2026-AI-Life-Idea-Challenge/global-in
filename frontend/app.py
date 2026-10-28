"""
frontend/app.py
Global-In Streamlit 앱 진입점
"""
import streamlit as st
import sys
import os

# 경로 설정 — frontend/ 폴더가 루트가 되도록
sys.path.insert(0, os.path.dirname(__file__))

from utils.session import (
    init_session,
    PAGE_HOME, PAGE_CHAT, PAGE_PROGRAMS, PAGE_PREPARATION, PAGE_PROFILE,
)

# ── 페이지 설정 ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Global-In",
    page_icon="⊙",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── 전역 스타일 ───────────────────────────────────────────────────────────
_style_path = os.path.join(os.path.dirname(__file__), "styles", "global.css")
if os.path.exists(_style_path):
    with open(_style_path, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── 세션 초기화 ───────────────────────────────────────────────────────────
init_session()

# ── 라우팅 ────────────────────────────────────────────────────────────────
page = st.session_state.get("page", PAGE_HOME)

if page == PAGE_HOME:
    from pages.home import render
    render()

elif page == PAGE_CHAT:
    from pages.chat import render
    render()

elif page == PAGE_PROGRAMS:
    from pages.programs import render
    render()

elif page == PAGE_PREPARATION:
    from pages.preparation import render
    render()

elif page == PAGE_PROFILE:
    from pages.profile import render
    render()

else:
    from pages.home import render
    render()
