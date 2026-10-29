"""
frontend/components/program_card.py
프로그램·지원제도 결과 카드 컴포넌트
"""
import streamlit as st


def render_program_card(program: dict, show_compare: bool = False):
    p_id = program.get("id", program.get("name", ""))
    p_type = program.get("type", "프로그램")
    badge_color = "#eef2ff" if p_type == "지원제도" else "#f0f0f0"
    badge_text_color = "#4f6ef7" if p_type == "지원제도" else "#555"

    if "saved_programs" not in st.session_state:
        st.session_state["saved_programs"] = {}

    is_saved = p_id in st.session_state["saved_programs"]

    col_main, col_actions = st.columns([5, 2])

    with col_main:
        type_html = (
            f'<span style="background:{badge_color}; color:{badge_text_color};'
            f' font-size:0.7rem; font-weight:600; padding:2px 8px;'
            f' border-radius:12px; margin-right:6px;">{p_type}</span>'
        )
        meta_html = (
            f'<span style="font-size:0.75rem; color:#888;">'
            f'{program.get("country","")}&nbsp;·&nbsp;{program.get("purpose","")}</span>'
        )
        st.markdown(
            f'<div style="margin-bottom:0.25rem;">{type_html}{meta_html}</div>',
            unsafe_allow_html=True,
        )

        emoji = program.get("country_emoji", "")
        name = program.get("name", "")
        st.markdown(
            f'<div style="font-size:1rem; font-weight:700; margin-bottom:0.2rem;">'
            f'{emoji}&nbsp;&nbsp;{name}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="font-size:0.85rem; color:#555; margin-bottom:0.2rem;">'
            f'{program.get("description","")}</div>',
            unsafe_allow_html=True,
        )
        condition = program.get("condition_summary", "")
        if condition:
            st.markdown(
                f'<div style="font-size:0.78rem; color:#999;">'
                f'대상·조건 &nbsp; {condition}</div>',
                unsafe_allow_html=True,
            )

    with col_actions:
        st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

        if show_compare:
            st.checkbox("비교하기", key=f"chk_compare_{p_id}")

        save_label = "계획에서 빼기" if is_saved else "내 계획에 담기"
        if st.button(save_label, key=f"save_{p_id}", use_container_width=True):
            saved = dict(st.session_state.get("saved_programs", {}))
            if is_saved:
                saved.pop(p_id, None)
            else:
                saved[p_id] = program
            st.session_state["saved_programs"] = saved
            st.rerun()

        url = program.get("url", "")
        if url:
            st.link_button("자세히 보기 ↗", url, use_container_width=True)
        else:
            if st.button("자세히 보기 ↗", key=f"detail_{p_id}", use_container_width=True):
                st.session_state["detail_program"] = program
                st.session_state["page"] = "program_detail"
                st.rerun()

    st.markdown(
        "<hr style='margin:0.75rem 0; border:none; border-top:1px solid #f5f5f5;'>",
        unsafe_allow_html=True,
    )