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


def _save_current_if_new(history: list):
    """현재 대화가 히스토리에 없는 경우에만 저장 (중복 방지)."""
    cur_msgs = st.session_state.get("chat_messages", [])
    cur_session_id = st.session_state.get("current_chat_id")
    user_msgs = [m for m in cur_msgs if m.get("role") == "user"]

    if not user_msgs:
        return  # 사용자 메시지 없으면 저장 불필요

    # current_chat_id 가 이미 히스토리에 있으면 중복 저장 금지
    if cur_session_id and any(s.get("session_id") == cur_session_id for s in history):
        return

    first_text = user_msgs[0].get("content", "대화")
    title = first_text[:22] + ("…" if len(first_text) > 22 else "")
    history.insert(0, {
        "title": title,
        "messages": cur_msgs.copy(),
        "session_id": cur_session_id,
    })


def render_inner_sidebar(active_page: str):
    st.markdown("""
    <style>
    div[data-testid="stButton"] button[kind="secondary"] {
        background: #ffffff !important;
        border: 1px solid #e0e0e0 !important;
        color: #333 !important;
        font-weight: 500;
    }
    </style>
    """, unsafe_allow_html=True)

    if active_page == PAGE_CHAT:
        if st.button("＋  새 채팅", key="sidebar_new_chat", use_container_width=True, type="secondary"):
            history = st.session_state.setdefault("chat_history", [])
            _save_current_if_new(history)
            # 새 대화 시작
            st.session_state["chat_messages"] = []
            st.session_state["chat_session_id"] = None
            st.session_state["current_chat_id"] = None
            st.session_state["chat_show_qr"] = True
            go_to(PAGE_CHAT)

        st.markdown(
            "<div style='font-size:0.7rem;font-weight:600;color:#aaa;"
            "letter-spacing:0.08em;margin:1rem 0 0.4rem;text-transform:uppercase;'>"
            "채팅 목록</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div style='background:#f0f0f0;border-radius:8px;padding:8px 12px;"
            "font-size:0.85rem;color:#333;display:flex;align-items:center;gap:8px;"
            "margin-bottom:4px;'>💬 새 채팅</div>",
            unsafe_allow_html=True,
        )
        history = st.session_state.get("chat_history", [])
        for idx, session in enumerate(history):
            label = session.get("title", f"대화 {idx+1}")
            if st.button(label, key=f"chat_hist_{idx}", use_container_width=True):
                # 현재 대화가 히스토리에 없는 경우만 저장 (중복 방지)
                _save_current_if_new(history)
                # 선택한 세션 복원
                st.session_state["restore_chat_session"] = session
                go_to(PAGE_CHAT)

        st.markdown("<hr style='border:none;border-top:1px solid #f0f0f0;margin:1rem 0 0.5rem;'>",
                    unsafe_allow_html=True)

    st.markdown(
        "<div style='font-size:0.7rem;font-weight:600;color:#aaa;"
        "letter-spacing:0.08em;margin-bottom:0.4rem;text-transform:uppercase;'>"
        "돌아보기</div>",
        unsafe_allow_html=True,
    )

    is_chat_active = active_page == PAGE_CHAT
    if st.button("💬  AI 상담", key="sidebar_nav_chat", use_container_width=True,
                 type="primary" if is_chat_active else "secondary"):
        go_to(PAGE_CHAT)

    for page_key, icon, label in NAV_ITEMS:
        is_active = page_key == active_page
        if st.button(f"{icon}  {label}", key=f"sidebar_nav_{page_key}",
                     use_container_width=True, type="primary" if is_active else "secondary"):
            go_to(page_key)

    st.markdown("<hr style='border:none;border-top:1px solid #f0f0f0;margin:0.75rem 0;'>",
                unsafe_allow_html=True)
    if st.button("👤  내 프로필", key="sidebar_profile", use_container_width=True, type="secondary"):
        go_to(PAGE_PROFILE)
