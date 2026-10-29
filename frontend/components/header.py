"""
frontend/components/header.py
글로벌 헤더
"""
import streamlit as st


def render_header(right_label: str = "", show_nav: bool = False):
    # 로고 버튼 CSS: 버튼을 로고처럼 보이게
    st.markdown("""
    <style>
    [data-testid="stBaseButton-secondary"][key="logo_home_btn"],
    button[kind="secondary"][data-testid="stBaseButton-secondary"].logo-btn {
        background: none !important;
        border: none !important;
        padding: 0 !important;
        cursor: pointer !important;
        box-shadow: none !important;
    }
    div[data-testid="column"]:has(button[key="logo_home_btn"]) button {
        background: none !important;
        border: none !important;
        padding: 0 !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        color: #1a1a1a !important;
        box-shadow: none !important;
        text-align: left !important;
    }
    div[data-testid="column"]:has(button[key="logo_home_btn"]) button:hover {
        color: #444 !important;
        background: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

    col_logo, col_right = st.columns([5, 2])

    with col_logo:
        st.markdown(
            "<div style='display:flex;align-items:center;gap:10px;padding:0.6rem 0;'>",
            unsafe_allow_html=True,
        )
        if st.button("⊙  Global-In .", key="logo_home_btn"):
            st.session_state["page"] = "home"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        st.markdown(
            f'<div style="text-align:right;font-size:0.85rem;color:#666;padding:0.6rem 0;">● {right_label}</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        "<hr style='margin:0 0 1rem;border:none;border-top:1px solid #e8e8e8;'>",
        unsafe_allow_html=True,
    )
