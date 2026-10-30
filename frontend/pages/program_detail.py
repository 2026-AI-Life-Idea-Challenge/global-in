"""
frontend/pages/program_detail.py
프로그램 상세 페이지
"""
import streamlit as st
from utils.session import go_to, PAGE_PROGRAMS, PAGE_CHAT
from utils.api import get_program_detail, get_program_detail_support, get_program_policies, _CONDITION_STATUS_WORDS

# 채팅 관련 위젯 키 클리어 (detail 페이지에서 chat form 잔상 방지)
for _k in ["chat_text_input", "FormSubmitter:chat_input_form-↑"]:
    st.session_state.pop(_k, None)


def render():
    program = st.session_state.get("selected_program")

    if not program:
        st.warning("선택된 프로그램 정보가 없습니다.")
        if st.button("← 프로그램 목록으로"):
            go_to(PAGE_PROGRAMS)
        return

    back_page = st.session_state.get("detail_back_page", PAGE_PROGRAMS)
    if st.button("← 돌아가기", key="pd_back"):
        go_to(back_page)

    st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

    p_type = program.get("type", "프로그램")
    badge_color = "#eef2ff" if p_type == "지원제도" else "#f0f0f0"
    badge_text_color = "#4f6ef7" if p_type == "지원제도" else "#555"

    country_emoji = program.get("country_emoji", "")
    country = program.get("country", "")
    purpose = program.get("purpose", "")

    st.markdown(
        f"""
        <div style="margin-bottom:0.5rem;">
            <span style="background:{badge_color}; color:{badge_text_color};
                font-size:0.72rem; font-weight:600; padding:3px 10px;
                border-radius:12px; margin-right:6px;">{p_type}</span>
            <span style="font-size:0.8rem; color:#888;">{country}&nbsp;·&nbsp;{purpose}</span>
        </div>
        <div style="font-size:1.5rem; font-weight:800; color:#1a1a1a; margin-bottom:0.25rem;">
            {country_emoji}&nbsp;&nbsp;{program.get("name", "")}
        </div>
        <hr style="margin:0.75rem 0; border:none; border-top:1px solid #e8e8e8;">
        """,
        unsafe_allow_html=True,
    )

    desc = program.get("description", "")
    if desc:
        _section("프로그램 소개")
        st.markdown(
            f'<div style="font-size:0.9rem; color:#333; line-height:1.7;">{desc}</div>',
            unsafe_allow_html=True,
        )

    program_id = program.get("id", "")
    is_support = (p_type == "지원제도")
    detail = {}
    policies = []
    if program_id:
        try:
            if is_support:
                detail = get_program_detail_support(program_id, program_name=program.get("name", "")) or {}
            else:
                detail = get_program_detail(program_id, program_name=program.get("name", "")) or {}
        except Exception:
            detail = {}
        try:
            policies = get_program_policies(program_id, program_type=p_type) or []
        except Exception:
            policies = []

    metadata = detail.get("metadata") or {}
    if isinstance(metadata, str):
        import json
        try:
            metadata = json.loads(metadata)
        except Exception:
            metadata = {}

    _dns = metadata.get("display_name_source") or {}
    if isinstance(_dns, str):
        import json as _j
        try:
            _dns = _j.loads(_dns)
        except Exception:
            _dns = {}
    _dns_url = _dns.get("source_url") if isinstance(_dns, dict) else ""

    official_url = (
        detail.get("official_url")
        or _dns_url
        or program.get("url")
        or metadata.get("url")
        or metadata.get("official_url")
        or metadata.get("source_url")
        or detail.get("url")
        or ""
    )

    condition = program.get("condition_summary", "").strip().rstrip(".")
    has_meaningful_condition = condition and condition not in _CONDITION_STATUS_WORDS

    _section("지원 조건 / 자격 요건")

    if policies:
        for pol in policies:
            topic = pol.get("topic") or ""
            text = pol.get("policy_text") or ""
            if not text:
                continue
            topic_html = (
                f'<span style="font-size:0.75rem;font-weight:700;color:#555;'
                f'background:#f5f5f5;padding:2px 8px;border-radius:8px;'
                f'margin-right:6px;">{topic}</span>'
                if topic else ""
            )
            st.markdown(
                f'<div style="margin-bottom:0.8rem;">'
                f'{topic_html}'
                f'<div style="font-size:0.88rem;color:#444;line-height:1.7;margin-top:0.3rem;">{text}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
    elif has_meaningful_condition:
        st.markdown(
            f'<div style="font-size:0.88rem; color:#555; line-height:1.7;">{condition}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="font-size:0.88rem;color:#aaa;">조건 정보를 준비 중이에요.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if official_url:
            st.link_button(
                "🌐  공식 홈페이지 방문",
                official_url,
                use_container_width=True,
                type="primary",
            )
        else:
            st.markdown(
                "<div style='font-size:0.85rem;color:#aaa;padding:0.6rem 0;'>"
                "공식 홈페이지 정보를 준비 중이에요.</div>",
                unsafe_allow_html=True,
            )

    with col2:
        if st.button("💬  이 프로그램 상담하기", key="pd_chat", use_container_width=True):
            prog_name = program.get("name", "")
            st.session_state["pending_chat_message"] = (
                f"{prog_name}에 대해 더 자세히 알고 싶어요."
            )
            go_to(PAGE_CHAT)

    p_id = program.get("id", program.get("name", ""))
    saved = st.session_state.get("saved_programs", {})
    is_saved = p_id in saved

    st.markdown("<div style='margin-top:0.75rem;'></div>", unsafe_allow_html=True)
    save_label = "📌 내 계획에서 빼기" if is_saved else "📌 내 계획에 담기"
    if st.button(save_label, key="pd_save", use_container_width=False):
        saved = dict(st.session_state.get("saved_programs", {}))
        if is_saved:
            saved.pop(p_id, None)
        else:
            saved[p_id] = program
        st.session_state["saved_programs"] = saved
        st.rerun()


def _section(title: str):
    st.markdown(
        f"""
        <div style="font-size:0.78rem; font-weight:600; letter-spacing:0.05em;
             color:#888; margin:1.2rem 0 0.5rem; text-transform:uppercase;">{title}</div>
        <hr style="margin:0 0 0.6rem; border:none; border-top:1px solid #f0f0f0;">
        """,
        unsafe_allow_html=True,
    )
