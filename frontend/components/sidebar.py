"""
frontend/components/sidebar.py
내부 사이드바 (inner nav)
"""
import streamlit as st
from utils.session import (
    PAGE_CHAT, PAGE_PROGRAMS, PAGE_PREPARATION, PAGE_PROFILE, go_to,
)

NAV_ITEMS = [
    (PAGE_PROGRAMS,    "⊙", "프로그램·지원제도 찾기"),
    (PAGE_PREPARATION, "≡", "내 준비"),
]


def render_inner_sidebar(active_page: str):
    with st.sidebar:
        st.markdown("""
        <style>
        [data-testid="stSidebarContent"] { background: #ffffff; }
        div[data-testid="stButton"] button[kind="secondary"] {
            background: #ffffff !important;
            border: 1px solid #e0e0e0 !important;
            color: #333 !important;
            font-weight: 500;
        }
        </style>
        """, unsafe_allow_html=True)

        if active_page == PAGE_CHAT:
            st.markdown("<hr style='border:none;border-top:1px solid #f0f0f0;margin:0.5rem 0;'>",
                        unsafe_allow_html=True)

            # 새 채팅 버튼 — 아웃라인 스타일
            if st.button("＋  새 채팅", key="sidebar_new_chat", use_container_width=True, type="secondary"):
                st.session_state["chat_messages"] = []
                st.session_state["chat_session_id"] = None
                go_to(PAGE_CHAT)

            st.markdown(
                "<div style='font-size:0.7rem; font-weight:600; color:#aaa; "
                "letter-spacing:0.08em; margin:1rem 0 0.4rem; text-transform:uppercase;'>"
                "채팅 목록</div>",
                unsafe_allow_html=True,
            )

            # 현재 채팅을 목록 첫 항목으로 표시
            st.markdown(
                "<div style='background:#f0f0f0;border-radius:8px;padding:8px 12px;"
                "font-size:0.85rem;color:#333;display:flex;align-items:center;gap:8px;"
                "margin-bottom:4px;'>💬 새 채팅</div>",
                unsafe_allow_html=True,
            )

            # 이전 채팅 히스토리
            history = st.session_state.get("chat_history", [])
            for idx, session in enumerate(history):
                label = session.get("title", f"대화 {idx+1}")
                if st.button(label, key=f"chat_hist_{idx}", use_container_width=True):
                    st.session_state["current_chat_idx"] = idx
                    go_to(PAGE_CHAT)

            st.markdown("<hr style='border:none;border-top:1px solid #f0f0f0;margin:1rem 0 0.5rem;'>",
                        unsafe_allow_html=True)

        # 돌아보기 섹션
        st.markdown(
            "<div style='font-size:0.7rem; font-weight:600; color:#aaa; "
            "letter-spacing:0.08em; margin-bottom:0.4rem; text-transform:uppercase;'>"
            "돌아보기</div>",
            unsafe_allow_html=True,
        )

        # AI 상담 (채팅 페이지 링크)
        is_chat_active = active_page == PAGE_CHAT
        if st.button(
            "💬  AI 상담",
            key="sidebar_nav_chat",
            use_container_width=True,
            type="primary" if is_chat_active else "secondary",
        ):
            go_to(PAGE_CHAT)

        for page_key, icon, label in NAV_ITEMS:
            is_active = page_key == active_page
            if st.button(
                f"{icon}  {label}",
                key=f"sidebar_nav_{page_key}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                go_to(page_key)

        # 내 프로필
        st.markdown("<div style='flex:1'></div>", unsafe_allow_html=True)
        st.markdown("<hr style='border:none;border-top:1px solid #f0f0f0;margin:0.75rem 0;'>",
                    unsafe_allow_html=True)
        if st.button("👤  내 프로필", key="sidebar_profile", use_container_width=True, type="secondary"):
            go_to(PAGE_PROFILE)