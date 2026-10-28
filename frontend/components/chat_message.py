"""
frontend/components/chat_message.py
채팅 메시지 버블 컴포넌트
"""
import streamlit as st


def render_message(role: str, content: str, programs: list | None = None):
    if role == "user":
        st.markdown(
            f"""
            <div style="display:flex; justify-content:flex-end; margin:0.5rem 0;">
                <div class="gi-chat-user">{content}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div style="display:flex; align-items:flex-start; gap:0.75rem; margin:0.5rem 0;">
                <div style="width:32px; height:32px; background:#1a1a1a;
                    border-radius:50%; display:flex; align-items:center;
                    justify-content:center; color:white; font-size:0.9rem;
                    flex-shrink:0; margin-top:2px;">⊙</div>
                <div>
                    <div style="font-size:0.78rem; font-weight:600; color:#333;
                         margin-bottom:0.35rem;">Global-In</div>
                    <div class="gi-chat-ai">
                        {content.replace(chr(10), "<br>")}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if programs:
            from components.program_card import render_program_card
            st.markdown(
                """
                <div style="margin:0.5rem 0 0.25rem 2.75rem; font-size:0.72rem;
                     font-weight:600; letter-spacing:0.06em; color:#888;">
                    PROGRAMS FOR YOU
                </div>
                """,
                unsafe_allow_html=True,
            )
            for prog in programs:
                with st.container():
                    render_program_card(prog, show_compare=True)


def render_quick_replies(options: list[str], key_prefix: str = "qr") -> str | None:
    """퀵리플라이 pill 버튼 그룹. gi-quick-reply-wrap 클래스로 CSS pill 적용."""
    # pill 스타일 적용을 위해 wrapper div
    st.markdown('<div class="gi-quick-reply-wrap">', unsafe_allow_html=True)
    cols = st.columns(len(options))
    selected = None
    for i, (col, opt) in enumerate(zip(cols, options)):
        with col:
            if st.button(opt, key=f"{key_prefix}_{i}", use_container_width=True):
                selected = opt
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown(
        "<div style='font-size:0.78rem; color:#aaa; margin:0.2rem 0 0.5rem;'>"
        "가까운 답변을 고르거나, 아래에 직접 적어 주세요.</div>",
        unsafe_allow_html=True,
    )
    return selected
