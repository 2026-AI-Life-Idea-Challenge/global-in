"""
frontend/pages/compare.py
프로그램 비교 페이지 — 선택된 프로그램들을 나란히 비교
"""
import streamlit as st
from utils.session import go_to, PAGE_PROGRAMS
from utils.api import get_program_policies, _CONDITION_STATUS_WORDS


def render():
    compared = st.session_state.get("compare_list", [])

    st.markdown("## 프로그램 비교")

    if len(compared) < 2:
        st.info("비교할 프로그램을 2개 이상 선택하세요. 프로그램 목록에서 '비교하기' 체크박스를 선택하세요.")
        if st.button("← 프로그램 목록으로"):
            go_to(PAGE_PROGRAMS)
        return

    if st.button("← 목록으로 돌아가기", key="cmp_back"):
        go_to(PAGE_PROGRAMS)

    st.markdown("<div style='margin-bottom:1rem;'></div>", unsafe_allow_html=True)

    # ── 헤더 행 ──────────────────────────────────────────────
    n = len(compared)
    cols = st.columns([1] + [2] * n)
    with cols[0]:
        st.markdown(
            "<div style='font-size:0.75rem;font-weight:700;color:#aaa;padding-top:0.5rem;'>항목</div>",
            unsafe_allow_html=True,
        )
    for i, prog in enumerate(compared):
        with cols[i + 1]:
            p_type = prog.get("type", "프로그램")
            badge_color = "#eef2ff" if p_type == "지원제도" else "#f0f0f0"
            badge_text_color = "#4f6ef7" if p_type == "지원제도" else "#555"
            emoji = prog.get("country_emoji", "")
            p_id = prog.get("id", prog.get("name", ""))
            st.markdown(
                f'<div style="text-align:center;">'
                f'<span style="background:{badge_color};color:{badge_text_color};'
                f'font-size:0.68rem;font-weight:600;padding:2px 8px;border-radius:10px;">{p_type}</span><br>'
                f'<span style="font-size:1rem;font-weight:800;color:#1a1a1a;">{emoji} {prog.get("name","")}</span><br>'
                f'<span style="font-size:0.78rem;color:#888;">{prog.get("country","")} · {prog.get("purpose","")}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button("✕ 제외", key=f"cmp_remove_{p_id}", use_container_width=True):
                compare_list = [p for p in compared if p.get("id", p.get("name", "")) != p_id]
                st.session_state["compare_list"] = compare_list
                st.session_state[f"chk_compare_{p_id}"] = False
                st.rerun()

    st.markdown("<hr style='margin:0.75rem 0;border:none;border-top:2px solid #1a1a1a;'>", unsafe_allow_html=True)

    # ── 비교 행들 ─────────────────────────────────────────────
    FIELDS = [
        ("국가", "country"),
        ("분류", "type"),
        ("목적", "purpose"),
        ("설명", "description"),
    ]

    for label, key in FIELDS:
        cols = st.columns([1] + [2] * n)
        with cols[0]:
            st.markdown(
                f'<div style="font-size:0.78rem;font-weight:600;color:#888;padding:0.5rem 0;">{label}</div>',
                unsafe_allow_html=True,
            )
        for i, prog in enumerate(compared):
            with cols[i + 1]:
                val = prog.get(key, "") or "-"
                st.markdown(
                    f'<div style="font-size:0.85rem;color:#333;padding:0.5rem 0;line-height:1.5;">{val}</div>',
                    unsafe_allow_html=True,
                )
        st.markdown("<hr style='margin:0.1rem 0;border:none;border-top:1px solid #f0f0f0;'>", unsafe_allow_html=True)

    # ── 지원 조건 비교 ────────────────────────────────────────
    _divider_label("지원 조건 / 자격 요건")
    cols = st.columns([1] + [2] * n)
    with cols[0]:
        st.markdown(
            '<div style="font-size:0.78rem;font-weight:600;color:#888;padding:0.5rem 0;">조건</div>',
            unsafe_allow_html=True,
        )
    for i, prog in enumerate(compared):
        with cols[i + 1]:
            p_id = prog.get("id", prog.get("name", ""))
            p_type = prog.get("type", "프로그램")
            policies = []
            if p_id:
                try:
                    policies = get_program_policies(p_id, program_type=p_type) or []
                except Exception:
                    policies = []

            condition = prog.get("condition_summary", "").strip().rstrip(".")
            has_condition = condition and condition not in _CONDITION_STATUS_WORDS

            if policies:
                items_html = ""
                for pol in policies[:5]:
                    topic = pol.get("topic") or ""
                    text = pol.get("policy_text") or ""
                    if not text:
                        continue
                    topic_span = (
                        f'<span style="font-size:0.68rem;font-weight:700;background:#f5f5f5;'
                        f'padding:1px 6px;border-radius:6px;margin-right:4px;">{topic}</span>'
                        if topic else ""
                    )
                    items_html += (
                        f'<div style="margin-bottom:0.5rem;">'
                        f'{topic_span}'
                        f'<div style="font-size:0.82rem;color:#444;line-height:1.5;margin-top:0.2rem;">{text}</div>'
                        f'</div>'
                    )
                st.markdown(
                    f'<div style="padding:0.5rem 0;">{items_html}</div>',
                    unsafe_allow_html=True,
                )
            elif has_condition:
                st.markdown(
                    f'<div style="font-size:0.82rem;color:#555;padding:0.5rem 0;line-height:1.5;">{condition}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div style="font-size:0.82rem;color:#bbb;padding:0.5rem 0;">준비 중</div>',
                    unsafe_allow_html=True,
                )

    st.markdown("<hr style='margin:1.5rem 0;border:none;border-top:1px solid #e8e8e8;'>", unsafe_allow_html=True)

    # ── 하단 액션 버튼 ────────────────────────────────────────
    action_cols = st.columns([1] + [2] * n)
    with action_cols[0]:
        st.markdown("")
    for i, prog in enumerate(compared):
        with action_cols[i + 1]:
            p_id = prog.get("id", prog.get("name", ""))
            if st.button("자세히 보기 →", key=f"cmp_detail_{p_id}", use_container_width=True, type="primary"):
                st.session_state["selected_program"] = prog
                st.session_state["detail_back_page"] = "compare"
                from utils.session import PAGE_PROGRAM_DETAIL
                go_to(PAGE_PROGRAM_DETAIL)


def _divider_label(title: str):
    st.markdown(
        f'<div style="font-size:0.75rem;font-weight:700;letter-spacing:0.05em;'
        f'color:#aaa;text-transform:uppercase;margin:1rem 0 0.3rem;">{title}</div>',
        unsafe_allow_html=True,
    )
