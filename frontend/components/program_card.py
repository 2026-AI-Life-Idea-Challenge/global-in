"""
frontend/components/program_card.py
프로그램·지원제도 결과 카드 컴포넌트
"""
import streamlit as st

MAX_COMPARE = 3


def _compare_ids() -> list[str]:
    return [
        p.get("id", p.get("name", ""))
        for p in st.session_state.get("compare_programs", [])
    ]


def render_program_card(program: dict, show_compare: bool = False):
    """
    program dict 필드:
        id, type, country, country_emoji, purpose, name, description, condition_summary
    """
    p_type = program.get("type", "프로그램")
    badge_color = "#eef2ff" if p_type == "지원제도" else "#f0f0f0"
    badge_text_color = "#4f6ef7" if p_type == "지원제도" else "#555"

    prog_id = program.get("id", program.get("name", ""))
    col_main, col_btn = st.columns([5, 1])

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

    with col_btn:
        st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)
        if st.button(
            "자세히 보기 ↗",
            key=f"detail_{prog_id}",
            use_container_width=True,
        ):
            st.session_state["detail_program"] = program
            st.session_state["page"] = "program_detail"
            st.rerun()

        if show_compare:
            compare_list: list = st.session_state.setdefault("compare_programs", [])
            is_selected = prog_id in _compare_ids()

            if is_selected:
                if st.button(
                    "✓ 선택됨",
                    key=f"compare_{prog_id}",
                    use_container_width=True,
                    type="primary",
                ):
                    st.session_state["compare_programs"] = [
                        p for p in compare_list
                        if p.get("id", p.get("name", "")) != prog_id
                    ]
                    st.rerun()
            else:
                at_max = len(compare_list) >= MAX_COMPARE
                if st.button(
                    "비교에 담기",
                    key=f"compare_{prog_id}",
                    use_container_width=True,
                    disabled=at_max,
                ):
                    st.session_state["compare_programs"].append(program)
                    st.rerun()

    st.markdown(
        "<hr style='margin:0.75rem 0; border:none; border-top:1px solid #f5f5f5;'>",
        unsafe_allow_html=True,
    )
