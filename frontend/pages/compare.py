"""
frontend/pages/compare.py
프로그램 나란히 비교 화면
"""
import streamlit as st
from components.header import render_header
from utils.session import PAGE_PROGRAMS, PAGE_CHAT, go_to

COMPARE_ROWS = [
    ("종류",      "type"),
    ("국가",      "country"),
    ("목적",      "purpose"),
    ("대상·조건", "condition_summary"),
    ("설명",      "description"),
]


def render():
    render_header(right_label="프로그램 비교")

    compare_list: list = st.session_state.get("compare_programs", [])

    if len(compare_list) < 2:
        st.markdown(
            "<div style='text-align:center;padding:3rem 0;color:#aaa;'>"
            "<div style='font-size:1.5rem;margin-bottom:0.5rem;'>⊙</div>"
            "<div style='font-size:0.9rem;'>비교할 프로그램을 2개 이상 선택해 주세요.</div>"
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button("← 프로그램 찾기로 돌아가기", key="back_to_programs"):
            go_to(PAGE_PROGRAMS)
        return

    st.markdown(
        "<div style='font-size:0.65rem;font-weight:700;letter-spacing:0.15em;"
        "color:#aaa;margin-bottom:0.2rem;'>● COMPARE</div>"
        "<h2 style='font-size:1.3rem;font-weight:700;margin:0 0 1rem;color:#1a1a1a;'>"
        "프로그램 비교</h2>",
        unsafe_allow_html=True,
    )

    n = len(compare_list)
    cols = st.columns(n)

    # 프로그램 헤더 카드
    for col, prog in zip(cols, compare_list):
        emoji  = prog.get("country_emoji", "")
        name   = prog.get("name", "")
        p_type = prog.get("type", "")
        badge_color = "#eef2ff" if p_type == "지원제도" else "#f0f0f0"
        badge_tc    = "#4f6ef7" if p_type == "지원제도" else "#555"
        with col:
            st.markdown(
                f"<div style='border:1px solid #e8e8e8;border-radius:12px;"
                f"padding:1rem;background:#fff;min-height:90px;'>"
                f"<span style='background:{badge_color};color:{badge_tc};"
                f"font-size:0.68rem;font-weight:600;padding:2px 8px;"
                f"border-radius:12px;'>{p_type}</span>"
                f"<div style='font-size:1rem;font-weight:700;margin-top:0.4rem;'>"
                f"{emoji}&nbsp;{name}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    st.markdown(
        "<hr style='margin:1rem 0;border:none;border-top:1px solid #f0f0f0;'>",
        unsafe_allow_html=True,
    )

    # 항목별 비교 행
    for label, field in COMPARE_ROWS:
        st.markdown(
            f"<div style='font-size:0.72rem;font-weight:700;color:#aaa;"
            f"letter-spacing:0.05em;margin-bottom:0.2rem;'>{label.upper()}</div>",
            unsafe_allow_html=True,
        )
        row_cols = st.columns(n)
        for col, prog in zip(row_cols, compare_list):
            value = prog.get(field, "—") or "—"
            with col:
                st.markdown(
                    f"<div style='font-size:0.85rem;color:#1a1a1a;"
                    f"padding:0.5rem 0;border-bottom:1px solid #f5f5f5;"
                    f"line-height:1.5;'>{value}</div>",
                    unsafe_allow_html=True,
                )
        st.markdown("<div style='margin-bottom:0.5rem;'></div>", unsafe_allow_html=True)

    st.markdown(
        "<hr style='margin:1rem 0;border:none;border-top:1px solid #f0f0f0;'>",
        unsafe_allow_html=True,
    )

    # 상담 연결 버튼 (프로그램별)
    st.markdown(
        "<div style='font-size:0.78rem;color:#aaa;margin-bottom:0.5rem;'>이 프로그램으로 상담 시작</div>",
        unsafe_allow_html=True,
    )
    action_cols = st.columns(n)
    for col, prog in zip(action_cols, compare_list):
        with col:
            name = prog.get("name", "")
            if st.button(
                f"{name} 상담하기 →",
                key=f"chat_from_compare_{prog.get('id', name)}",
                use_container_width=True,
                type="primary",
            ):
                st.session_state["chat_context_program"] = prog
                go_to(PAGE_CHAT)

    st.markdown("<div style='margin-top:0.75rem;'></div>", unsafe_allow_html=True)

    back_col, clear_col = st.columns([3, 1])
    with back_col:
        if st.button("← 프로그램 찾기로 돌아가기", key="back_programs", use_container_width=True):
            go_to(PAGE_PROGRAMS)
    with clear_col:
        if st.button("비교 초기화", key="clear_compare_page", use_container_width=True):
            st.session_state["compare_programs"] = []
            go_to(PAGE_PROGRAMS)
