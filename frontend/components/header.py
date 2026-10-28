"""
frontend/components/header.py
글로벌 헤더
"""
import streamlit as st


def render_header(right_label: str = "", show_nav: bool = False):
    st.markdown(
        f"""
        <div style="
            background:#ffffff;
            border:1px solid #e8e8e8;
            border-radius:16px;
            padding:0.6rem 1.5rem;
            display:flex;
            justify-content:space-between;
            align-items:center;
            margin-bottom:0.75rem;
        ">
            <div style="font-size:1rem; font-weight:700; color:#1a1a1a;">⊙  Global-In .</div>
            <div style="font-size:0.8rem; color:#888;">● {right_label}</div>
        </div>
        <hr style="margin:0 0 0.75rem; border:none; border-top:1px solid #e8e8e8;">
        """,
        unsafe_allow_html=True,
    )