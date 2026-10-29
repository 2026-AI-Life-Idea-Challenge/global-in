"""
frontend/components/header.py
글로벌 헤더
"""
import streamlit as st


def render_header(right_label: str = "", show_nav: bool = False):
    st.markdown(
        f"""
        <style>
        [data-testid="stToolbar"],[data-testid="stDecoration"],footer,#MainMenu {{
            display:none !important;
        }}
        </style>
        <div style="
            background:#ffffff;
            border-bottom:1px solid #e8e8e8;
            padding:1rem 2rem;
            display:flex;
            justify-content:space-between;
            align-items:center;
            margin-bottom:1.5rem;
        ">
            <div style="display:flex;align-items:center;gap:10px;">
                <div style="
                    width:36px;height:36px;
                    background:#111;
                    border-radius:8px;
                    display:flex;align-items:center;justify-content:center;
                    color:#fff;font-size:1rem;
                ">⊙</div>
                <span style="font-size:1.1rem;font-weight:700;color:#1a1a1a;">Global-In .</span>
            </div>
            <div style="font-size:0.85rem;color:#666;">● {right_label}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )