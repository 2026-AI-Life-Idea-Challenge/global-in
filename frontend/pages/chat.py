"""
frontend/pages/chat.py
AI 상담 화면
"""
import streamlit as st
from components.header import render_header
from components.sidebar import render_inner_sidebar
from components.chat_message import render_message, render_quick_replies
from utils.session import (
    PAGE_CHAT, get_current_chat, append_message, new_chat_session, get_profile,
)
from utils.api import chat_stream

QUICK_REPLIES_INITIAL = [
    "일본 취업을 알아보고 싶어요",
    "여러 나라를 비교하고 싶어요",
    "국가와 목적부터 정하고 싶어요",
]


def render():
    render_header(right_label="맞춤 상담")
    render_inner_sidebar(PAGE_CHAT)

    # 채팅 세션 없으면 생성
    if not st.session_state.get("current_chat_id"):
        new_chat_session()

    chat = get_current_chat()
    if chat is None:
        new_chat_session()
        chat = get_current_chat()

    messages = chat.get("messages", [])

    # 헤더 영역
    st.markdown(
        """
        <div style="text-align:center; padding:1.5rem 0 1rem;">
            <div style="font-size:0.7rem; font-weight:600; letter-spacing:0.14em;
                 color:#aaa; margin-bottom:0.5rem;">PERSONAL CONSULTATION</div>
            <div style="font-size:1.1rem; font-weight:700; color:#1a1a1a;">
                무엇이든 편하게 물어보세요
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 첫 화면 — 퀵리플라이
    if not messages:
        selected = render_quick_replies(QUICK_REPLIES_INITIAL, key_prefix="initial_qr")
        if selected:
            _send_message(selected, chat)
            st.rerun()

    # 메시지 렌더링
    for msg in messages:
        render_message(
            role=msg["role"],
            content=msg["content"],
            programs=msg.get("programs"),
        )

    # 추가 퀵리플라이 (AI 마지막 응답에 있으면)
    if messages:
        last = messages[-1]
        if last["role"] == "assistant" and last.get("quick_replies"):
            selected = render_quick_replies(last["quick_replies"], key_prefix="follow_qr")
            if selected:
                _send_message(selected, chat)
                st.rerun()

    # 입력창
    st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
    col_input, col_btn = st.columns([5, 1])
    with col_input:
        user_input = st.text_input(
            "",
            placeholder="편하게 이야기해 주세요.",
            label_visibility="collapsed",
            key="chat_input",
        )
    with col_btn:
        send_clicked = st.button("전송", key="chat_send", use_container_width=True, type="primary")

    if send_clicked and user_input.strip():
        _send_message(user_input.strip(), chat)
        st.rerun()


def _send_message(text: str, chat: dict):
    append_message("user", text)
    profile = get_profile()

    # API 호출 (스트리밍 응답은 현재 단순 수신)
    response = chat_stream(
        session_id=chat["id"],
        message=text,
        profile=profile,
    )

    append_message(
        "assistant",
        response.get("content", ""),
        extra={
            "programs": response.get("programs"),
            "quick_replies": response.get("quick_replies"),
        },
    )
    # 채팅 제목 자동 설정 (첫 메시지로)
    if len(chat.get("messages", [])) <= 2:
        chat["title"] = text[:20] + ("…" if len(text) > 20 else "")
