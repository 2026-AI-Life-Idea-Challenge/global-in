"""
frontend/pages/chat.py
AI 상담 화면 — 와이어프레임 image5/6 기준
"""
import streamlit as st
from components.header import render_header
from components.sidebar import render_inner_sidebar
from components.chat_message import render_message, render_quick_replies
from components.program_card import render_program_card
from utils.session import PAGE_CHAT, go_to, get_profile, save_profile
from utils.api import chat_send
from utils.session import new_chat_session

INITIAL_QUICK_REPLIES = [
    "워킹홀리데이 알아보기",
    "유학 조건 확인하기",
    "취업 비자 찾기",
    "내 조건에 맞는 나라 추천",
]

AI_GREETING = (
    "안녕하세요! 저는 Global-In AI예요. 😊\n\n"
    "해외 취업, 유학, 워킹홀리데이에 대해 궁금한 점을 편하게 이야기해 주세요. "
    "조건에 딱 맞는 프로그램을 찾아드릴게요."
)


def _render_program_section(programs: list, msg_idx: int):
    """AI 응답 아래 추천 프로그램 카드 섹션."""
    if not programs:
        return

    st.markdown(
        "<div style='margin:0.75rem 0 0.25rem 2.75rem;'>"
        "<span style='font-size:0.7rem;font-weight:700;letter-spacing:0.1em;"
        "color:#888;'>✦ 추천 프로그램</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    with st.container():
        for prog in programs:
            render_program_card(prog, show_compare=True)


def render():

    # 내 프로필 반영 중 배지
    profile = get_profile()
    if profile.get("nationalities") or profile.get("age"):
        st.markdown(
            "<div style='display:inline-flex;align-items:center;gap:0.4rem;"
            "background:#f8f8f8;border-radius:999px;padding:0.25rem 0.75rem;"
            "font-size:0.75rem;color:#555;margin-bottom:0.5rem;'>"
            "<span style='width:6px;height:6px;background:#1a1a1a;border-radius:50%;"
            "display:inline-block;'></span> 내 프로필 반영 중</div>",
            unsafe_allow_html=True,
        )

    # 메시지 초기화
    if "chat_messages" not in st.session_state or not st.session_state["chat_messages"]:
        st.session_state["chat_messages"] = [
            {"role": "ai", "content": AI_GREETING, "programs": []}
        ]
        st.session_state.setdefault("chat_show_qr", True)

    messages = st.session_state["chat_messages"]

    # 빈 채팅 상태 헤더
    if len(messages) == 1 and messages[0]["role"] == "ai":
        st.markdown(
            "<div style='text-align:center;padding:1.5rem 0 0.5rem;'>"
            "<span style='font-size:0.65rem;font-weight:700;letter-spacing:0.15em;"
            "color:#aaa;'>● PERSONAL CONSULTATION</span><br>"
            "<span style='font-size:1.6rem;font-weight:700;color:#1a1a1a;"
            "line-height:1.2;'>새 채팅</span>"
            "</div>",
            unsafe_allow_html=True,
        )

    # 메시지 + 프로그램 카드 렌더링
    for i, msg in enumerate(messages):
        render_message(msg["role"], msg["content"])

        # AI 메시지에 추천 프로그램이 있으면 카드 표시
        if msg["role"] == "ai":
            programs = msg.get("programs") or []
            _render_program_section(programs, i)

    # 첫 빠른 답변
    if st.session_state.get("chat_show_qr", False):
        selected = render_quick_replies(INITIAL_QUICK_REPLIES, key_prefix="init_qr")
        if selected:
            _send_message(selected)

    # 구분선
    st.markdown(
        "<hr style='border:none;border-top:1px solid #f0f0f0;margin:1rem 0 0.5rem;'>",
        unsafe_allow_html=True,
    )

    # 입력창
    with st.form("chat_input_form", clear_on_submit=True):
        cols = st.columns([10, 1])
        with cols[0]:
            user_input = st.text_input(
                "",
                placeholder="편하게 이야기해 주세요.",
                label_visibility="collapsed",
                key="chat_text_input",
            )
        with cols[1]:
            submitted = st.form_submit_button("↑")

    if submitted and user_input.strip():
        _send_message(user_input.strip())


def _send_message(text: str):
    messages = st.session_state.setdefault("chat_messages", [])
    messages.append({"role": "user", "content": text, "programs": []})
    st.session_state["chat_show_qr"] = False

    # session_id 없으면 새로 생성
    session_id = st.session_state.get("current_chat_id")
    if not session_id:
        session_id = new_chat_session()

    profile = get_profile()

    # history 변환 (ai → assistant)
    history = [
        {
            "role": "assistant" if m["role"] == "ai" else m["role"],
            "content": m["content"],
        }
        for m in messages[:-1]
    ]

    with st.spinner(""):
        reply_data = chat_send(
            user_query=text,
            session_id=session_id,
            history=history,
            profile=profile,
        )

    # 응답 언패킹
    if isinstance(reply_data, dict):
        reply_text = reply_data.get("text", "")
        programs = reply_data.get("programs") or []
        profile_updates = reply_data.get("profile") or {}
    else:
        reply_text = reply_data
        programs = []
        profile_updates = {}

    messages.append({"role": "ai", "content": reply_text, "programs": programs})

    # 대화에서 추출된 프로필 정보 반영
    if profile_updates:
        save_profile(profile_updates)

    st.rerun()
