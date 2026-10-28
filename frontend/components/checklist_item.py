"""
frontend/components/checklist_item.py
준비 체크리스트 항목 컴포넌트
"""
import streamlit as st


STATUS_LABELS = {
    "done": ("완료", "#22c55e"),
    "in_progress": ("수정", "#f59e0b"),
    "todo": ("", "#aaa"),
}


def render_checklist_item(item: dict, idx: int):
    """
    item 필드:
        title: str
        description: str
        status: 'done' | 'in_progress' | 'todo'
        tags: list[str]  — 예: ['공식 준비 항목', 'AI 추천']
        checked: bool
        official_link: str | None
        official_source: str | None
    """
    status = item.get("status", "todo")
    status_label, status_color = STATUS_LABELS.get(status, ("", "#aaa"))
    checked = item.get("checked", False)
    title = item.get("title", "")
    desc = item.get("description", "")
    tags = item.get("tags", [])
    official_link = item.get("official_link")
    official_source = item.get("official_source")

    col_chk, col_body, col_status = st.columns([0.5, 8, 1.5])

    with col_chk:
        st.markdown("<div style='padding-top:0.6rem;'></div>", unsafe_allow_html=True)
        new_checked = st.checkbox(
            "",
            value=checked,
            key=f"chk_{idx}",
            label_visibility="collapsed",
        )
        if new_checked != checked:
            item["checked"] = new_checked
            if new_checked:
                item["status"] = "done"
            st.rerun()

    with col_body:
        # 태그
        if tags:
            tags_html = " ".join(
                f'<span style="background:#f0f0f0; color:#555; font-size:0.68rem;'
                f' padding:2px 8px; border-radius:10px; margin-right:4px;">{t}</span>'
                for t in tags
            )
            st.markdown(tags_html, unsafe_allow_html=True)

        # 제목
        title_style = "text-decoration:line-through; color:#aaa;" if checked else "font-weight:600;"
        st.markdown(
            f'<div style="{title_style} font-size:0.9rem; margin:0.15rem 0;">{title}</div>',
            unsafe_allow_html=True,
        )

        # 설명
        if desc:
            st.markdown(
                f'<div style="font-size:0.8rem; color:#777; margin-bottom:0.2rem;">{desc}</div>',
                unsafe_allow_html=True,
            )

        # 공식 정보 링크
        if official_link and official_source:
            st.markdown(
                f'<a href="{official_link}" target="_blank" style="font-size:0.75rem;'
                f' color:#555; text-decoration:none;">📄 공식 정보 확인하기 ↗ &nbsp;'
                f'<span style="color:#aaa;">{official_source}</span></a>',
                unsafe_allow_html=True,
            )

    with col_status:
        if status_label:
            st.markdown(
                f'<div style="color:{status_color}; font-size:0.78rem;'
                f' font-weight:600; text-align:right; padding-top:0.6rem;">'
                f'{status_label}</div>',
                unsafe_allow_html=True,
            )

    st.markdown(
        "<hr style='margin:0.4rem 0; border:none; border-top:1px solid #f5f5f5;'>",
        unsafe_allow_html=True,
    )
