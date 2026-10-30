import streamlit as st
from utils.api import search_programs

COMPARE_FIELDS = [
    ("국가", "country"),
    ("분류", "type"),
    ("목적", "purpose"),
    ("대상·조건", "condition_summary"),
    ("설명", "description"),
]

@st.cache_data(ttl=60)
def _get_programs(tab, country, purpose, keyword):
    return search_programs({
        "tab": tab,
        "country": country,
        "purpose": purpose,
        "keyword": keyword,
    })

def render():
    from components.program_card import render_program_card
    from components.header import render_header

    st.markdown("## 프로그램·지원제도 찾기")

    query = st.text_input("", placeholder="검색어를 입력하세요 (예: 취업비자, 창업 지원...)", label_visibility="collapsed")

    tab_options = ["전체", "프로그램", "지원제도"]
    if "active_tab" not in st.session_state:
        st.session_state["active_tab"] = "전체"

    tab_cols = st.columns(len(tab_options))
    for i, tab_name in enumerate(tab_options):
        with tab_cols[i]:
            is_active = st.session_state["active_tab"] == tab_name
            btn_style = "primary" if is_active else "secondary"
            if st.button(tab_name, key=f"tab_{tab_name}", type=btn_style, use_container_width=True):
                st.session_state["active_tab"] = tab_name
                st.rerun()

    active_tab = st.session_state["active_tab"]

    st.markdown("**국가**")
    country_options = ["전체", "일본", "독일", "캐나다", "호주", "UAE"]
    if "active_country" not in st.session_state:
        st.session_state["active_country"] = "전체"
    country_cols = st.columns(len(country_options))
    for i, c in enumerate(country_options):
        with country_cols[i]:
            if st.button(c, key=f"country_{c}", type="primary" if st.session_state["active_country"] == c else "secondary", use_container_width=True):
                st.session_state["active_country"] = c
                st.rerun()
    active_country = st.session_state["active_country"]

    st.markdown("**목적**")
    purpose_options = ["전체", "취업", "창업", "학업", "생활정착", "투자"]
    if "active_purpose" not in st.session_state:
        st.session_state["active_purpose"] = "전체"
    purpose_cols = st.columns(len(purpose_options))
    for i, p in enumerate(purpose_options):
        with purpose_cols[i]:
            if st.button(p, key=f"purpose_{p}", type="primary" if st.session_state["active_purpose"] == p else "secondary", use_container_width=True):
                st.session_state["active_purpose"] = p
                st.rerun()
    active_purpose = st.session_state["active_purpose"]

    if st.button("↺ 초기화", key="reset_filters"):
        st.session_state["active_tab"] = "전체"
        st.session_state["active_country"] = "전체"
        st.session_state["active_purpose"] = "전체"
        st.rerun()

    st.markdown("---")

    programs = _get_programs(
        active_tab,
        active_country,
        active_purpose,
        query.strip() if query else "",
    )

    if not programs:
        st.info("조건에 맞는 프로그램이 없습니다.")
        return

    # ── 비교하기 ─────────────────────────────────────────────
    compare_keys = [
        f"chk_compare_{prog.get('id', prog.get('name', ''))}"
        for prog in programs
    ]
    compared = [
        prog for prog in programs
        if st.session_state.get(f"chk_compare_{prog.get('id', prog.get('name', ''))}")
    ]
    st.session_state["compare_list"] = compared

    if len(compared) >= 2:
        st.markdown(
            f'<div style="background:#f8f9ff;border:1px solid #dde3ff;border-radius:12px;'
            f'padding:0.75rem 1rem;margin-bottom:1rem;">'
            f'<span style="font-size:0.85rem;font-weight:700;color:#4f6ef7;">📊 {len(compared)}개 선택됨</span>'
            f'<span style="font-size:0.82rem;color:#666;margin-left:0.5rem;">'
            + ", ".join(p.get("name", "") for p in compared) +
            f'</span></div>',
            unsafe_allow_html=True,
        )
        col_cmp, col_clr = st.columns([2, 1])
        with col_cmp:
            if st.button("📊 선택 항목 비교하기", key="go_compare", type="primary", use_container_width=True):
                from utils.session import PAGE_COMPARE
                go_to(PAGE_COMPARE)
        with col_clr:
            if st.button("선택 초기화", key="clear_compare", use_container_width=True):
                for k in compare_keys:
                    st.session_state[k] = False
                st.session_state["compare_list"] = []
                st.rerun()

    st.markdown(f"**총 {len(programs)}개** 결과")
    for prog in programs:
        render_program_card(prog, show_compare=True)
        st.markdown("---")