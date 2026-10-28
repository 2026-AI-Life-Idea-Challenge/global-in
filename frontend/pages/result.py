"""
frontend/pages/result.py
상담 결과 화면 — 와이어프레임 기준
"""
import streamlit as st
from components.header import render_header
from utils.session import PAGE_CHAT, PAGE_PROGRAMS, PAGE_PREPARATION, PAGE_COMPARE, go_to

# ── 샘플 데이터 ────────────────────────────────────────────
SAMPLE_RESULT = {
    "summary": "워킹홀리데이 비자를 통해 호주·캐나다에서 취업 경험을 쌓고, 이후 유학으로 연결하는 경로가 가장 적합해 보여요.",
    "tags": ["워킹홀리데이", "호주", "캐나다", "영어권"],
    "programs": [
        {
            "id": "au_whv",
            "name": "호주 워킹홀리데이 비자",
            "country": "호주",
            "country_emoji": "🇦🇺",
            "type": "프로그램",
            "purpose": "워킹홀리데이",
            "match_pct": 92,
            "description": "만 18~30세 대상, 최대 3년 체류 가능. 영어 실력 향상과 실무 경험을 동시에.",
            "condition_summary": "만 18~30세, 여권 보유, 건강 조건 충족",
        },
        {
            "id": "ca_whv",
            "name": "캐나다 워킹홀리데이 비자 (IEC)",
            "country": "캐나다",
            "country_emoji": "🇨🇦",
            "type": "프로그램",
            "purpose": "워킹홀리데이",
            "match_pct": 85,
            "description": "IEC 프로그램을 통해 최대 2년 체류. 다양한 산업 분야 취업 가능.",
            "condition_summary": "만 18~35세, 영어 또는 불어 기본 구사",
        },
        {
            "id": "de_job_seeker",
            "name": "독일 구직 비자",
            "country": "독일",
            "country_emoji": "🇩🇪",
            "type": "프로그램",
            "purpose": "취업",
            "match_pct": 71,
            "description": "독일 취업을 목표로 최대 6개월 체류하며 구직 활동 가능.",
            "condition_summary": "학사 이상, 독일어 B1 이상 또는 영어 B2 이상",
        },
    ],
    "next_steps": [
        "여권 유효기간 확인 (출발 기준 6개월 이상)",
        "호주 WHV 신청 — 온라인 접수 (약 2~4주 소요)",
        "출발 전 영어 회화 기초 다지기",
        "현지 도착 후 세금 파일 번호 (TFN) 신청",
        "숙소 및 초반 정착 계획 수립",
    ],
    "cautions": [
        "워킹홀리데이 비자는 국가별로 연 1회만 신청 가능해요.",
        "체류 기간 연장은 지정 업종(농업·건설 등) 근무 조건을 충족해야 해요.",
        "비자 승인 후 12개월 이내에 첫 입국을 해야 해요.",
    ],
}


def render():
    render_header(right_label="상담 결과")

    result = st.session_state.get("consultation_result", SAMPLE_RESULT)

    # ── AI 분석 요약 배너 ──────────────────────────────────
    tags_html = "".join(
        f"<span style='background:#f0f0f0;color:#555;font-size:0.72rem;"
        f"font-weight:600;padding:3px 10px;border-radius:999px;'>{t}</span> "
        for t in result.get("tags", [])
    )
    st.markdown(
        f"<div style='background:#f8f8f8;border-radius:12px;padding:1.25rem 1.5rem;"
        f"margin-bottom:1.25rem;'>"
        f"<div style='font-size:0.65rem;font-weight:700;letter-spacing:0.15em;"
        f"color:#aaa;margin-bottom:0.4rem;'>● AI 분석 요약</div>"
        f"<div style='font-size:0.92rem;color:#1a1a1a;font-weight:500;"
        f"line-height:1.6;margin-bottom:0.75rem;'>{result['summary']}</div>"
        f"<div style='display:flex;gap:0.4rem;flex-wrap:wrap;'>{tags_html}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── 추천 프로그램 카드 ─────────────────────────────────
    st.markdown(
        "<div style='font-size:0.65rem;font-weight:700;letter-spacing:0.15em;"
        "color:#aaa;margin-bottom:0.4rem;'>● 추천 프로그램</div>",
        unsafe_allow_html=True,
    )

    for prog in result.get("programs", []):
        pct = prog.get("match_pct", 0)
        bar_color = "#1a1a1a" if pct >= 85 else "#888"
        col_info, col_pct = st.columns([5, 1])
        with col_info:
            st.markdown(
                f"<div style='border:1px solid #ebebeb;border-radius:12px;"
                f"padding:1rem 1.25rem;margin-bottom:0.75rem;'>"
                f"<div style='font-size:0.7rem;color:#aaa;margin-bottom:0.25rem;'>"
                f"{prog.get('country_emoji','')} {prog.get('country','')} · {prog.get('purpose','')}</div>"
                f"<div style='font-size:1rem;font-weight:700;color:#1a1a1a;margin-bottom:0.25rem;'>"
                f"{prog.get('name','')}</div>"
                f"<div style='font-size:0.83rem;color:#555;margin-bottom:0.2rem;'>"
                f"{prog.get('description','')}</div>"
                f"<div style='font-size:0.75rem;color:#999;'>대상·조건 &nbsp;"
                f"{prog.get('condition_summary','')}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )
        with col_pct:
            st.markdown(
                f"<div style='text-align:center;padding-top:1.25rem;'>"
                f"<div style='font-size:1.4rem;font-weight:800;color:{bar_color};'>{pct}%</div>"
                f"<div style='font-size:0.65rem;color:#aaa;'>매칭</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # ── 다음 단계 체크리스트 ───────────────────────────────
    st.markdown("<div style='margin-top:0.5rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='font-size:0.65rem;font-weight:700;letter-spacing:0.15em;"
        "color:#aaa;margin-bottom:0.6rem;'>● 다음 단계</div>",
        unsafe_allow_html=True,
    )
    steps = result.get("next_steps", [])
    for i, step in enumerate(steps, 1):
        st.markdown(
            f"<div style='display:flex;align-items:flex-start;gap:0.75rem;"
            f"padding:0.6rem 0;border-bottom:1px solid #f5f5f5;'>"
            f"<span style='min-width:24px;height:24px;background:#1a1a1a;color:#fff;"
            f"border-radius:50%;font-size:0.72rem;font-weight:700;"
            f"display:flex;align-items:center;justify-content:center;'>{i}</span>"
            f"<span style='font-size:0.85rem;color:#1a1a1a;line-height:1.5;'>{step}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # ── 유의사항 ───────────────────────────────────────────
    st.markdown("<div style='margin-top:1rem;'></div>", unsafe_allow_html=True)
    caution_items = "".join(
        f"<li style='margin-bottom:0.4rem;font-size:0.82rem;color:#555;'>{c}</li>"
        for c in result.get("cautions", [])
    )
    st.markdown(
        f"<div style='background:#fff8f0;border-left:3px solid #f0a040;"
        f"border-radius:0 8px 8px 0;padding:1rem 1.25rem;margin-top:0.5rem;'>"
        f"<div style='font-size:0.72rem;font-weight:700;color:#c07030;"
        f"margin-bottom:0.5rem;'>⚠ 유의사항</div>"
        f"<ul style='margin:0;padding-left:1.1rem;'>{caution_items}</ul>"
        f"</div>",
        unsafe_allow_html=True,
    )

    # ── 하단 버튼 ──────────────────────────────────────────
    st.markdown("<div style='margin-top:1.5rem;'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("💬 추가 질문하기", key="result_to_chat", use_container_width=True):
            go_to(PAGE_CHAT)
    with col2:
        if st.button("⊙ 프로그램 더 보기", key="result_to_programs", use_container_width=True):
            go_to(PAGE_PROGRAMS)
    with col3:
        if st.button("≡ 내 계획에 추가", key="result_to_prep", use_container_width=True, type="primary"):
            _add_to_preparation(steps)
            go_to(PAGE_PREPARATION)


def _add_to_preparation(next_steps: list[str]):
    items = st.session_state.setdefault("preparation_items", [])
    existing = {item.get("text", "") for item in items}
    for step in next_steps:
        if step not in existing:
            items.append({"text": step, "done": False})
