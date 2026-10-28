"""
frontend/components/sidebar.py
내부 사이드바 (inner nav)
"""
import streamlit as st
from utils.session import (
    PAGE_CHAT, PAGE_PROGRAMS, PAGE_PREPARATION, PAGE_PROFILE,
    PAGE_RESULT, PAGE_COMPARE, go_to,
)

NAV_ITEMS = [
    (PAGE_CHAT,        "💬", "AI 상담"),
    (PAGE_PROGRAMS,    "⊙", "프로그램·지원제도 찾기"),
    (PAGE_PREPARATION, "≡", "내 준비"),
]


def render_inner_sidebar(active_page: str):
    with st.sidebar:
        # 새 채팅 버튼
        if st.button("+ 새 채팅", key="sidebar_new_chat", use_container_width=True, type="primary"):
            st.session_state["chat_messages"] = []
            st.session_state["chat_session_id"] = None
            go_to(PAGE_CHAT)

        st.markdown(
            "<div style='font-size:0.7rem; font-weight:600; color:#aaa; "
            "letter-spacing:0.08em; margin:1rem 0 0.4rem; text-transform:uppercase;'>"
            "채팅 목록</div>",
            unsafe_allow_html=True,
        )

        # 채팅 히스토리 목록 (샘플)
        history = st.session_state.get("chat_history", [])
        if history:
            for idx, session in enumerate(history):
                label = session.get("title", f"대화 {idx+1}")
                if st.button(label, key=f"chat_hist_{idx}", use_container_width=True):
                    st.session_state["current_chat_idx"] = idx
                    go_to(PAGE_CHAT)
        else:
            st.markdown(
                "<div style='font-size:0.78rem; color:#ccc; padding:0.4rem 0;'>"
                "이전 대화가 없어요.</div>",
                unsafe_allow_html=True,
            )

        st.markdown("<hr style='border:none;border-top:1px solid #f0f0f0;margin:1rem 0 0.5rem;'>",
                    unsafe_allow_html=True)

        # 돌아보기 섹션
        st.markdown(
            "<div style='font-size:0.7rem; font-weight:600; color:#aaa; "
            "letter-spacing:0.08em; margin-bottom:0.4rem; text-transform:uppercase;'>"
            "돌아보기</div>",
            unsafe_allow_html=True,
        )

        for page_key, icon, label in NAV_ITEMS:
            is_active = page_key == active_page
            btn_label = f"{icon}  {label}"
            if st.button(
                btn_label,
                key=f"sidebar_nav_{page_key}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                go_to(page_key)

        # 내 프로필 (하단 고정 영역처럼)
        st.markdown("<div style='flex:1'></div>", unsafe_allow_html=True)
        st.markdown("<hr style='border:none;border-top:1px solid #f0f0f0;margin:0.75rem 0;'>",
                    unsafe_allow_html=True)
        if st.button("내 프로필", key="sidebar_profile", use_container_width=True):
            go_to(PAGE_PROFILE)
