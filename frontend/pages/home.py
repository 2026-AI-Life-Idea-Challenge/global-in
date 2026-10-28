"""
frontend/pages/home.py
홈화면 — 원본 디자인 완전 매칭
"""
import streamlit as st
from utils.session import go_to, PAGE_CHAT, PAGE_PROFILE


def render():
    # ── 헤더 ──────────────────────────────────────────────────
    left, right = st.columns([1, 1])
    with left:
        if st.button("⊙  Global-In .", key="header_logo", help="홈으로"):
            pass  # 이미 홈
    with right:
        c1, c2 = st.columns(2)
        with c1:
            st.button("서비스 소개", key="nav_intro", use_container_width=True)
        with c2:
            st.button("이용 방법", key="nav_howto", use_container_width=True)
    st.markdown(
        "<hr style='margin:0.4rem 0 0 0; border:none; border-top:1px solid #f0f0f0;'>",
        unsafe_allow_html=True,
    )

    # ── HERO — 국기 원형 + 텍스트 ─────────────────────────────
    st.markdown(
        """
        <div style="position:relative; width:100%; max-width:760px;
             margin:2rem auto 0; height:420px;">

          <!-- 원형 테두리 (배경 원) -->
          <div style="position:absolute; top:50%; left:50%;
               transform:translate(-50%,-50%);
               width:340px; height:340px;
               border:1.5px solid #e8e8e8; border-radius:50%;"></div>
          <div style="position:absolute; top:50%; left:50%;
               transform:translate(-50%,-50%);
               width:480px; height:480px;
               border:1px solid #f2f2f2; border-radius:50%;"></div>

          <!-- 국기 배치 (6개: 일본/미국/호주/독일/캐나다/한국) -->
          <!-- 일본 — 상단 좌측 -->
          <div style="position:absolute; top:48px; left:140px; text-align:center;">
            <div style="width:52px; height:52px; background:#fff;
                 border:1px solid #eee; border-radius:50%;
                 display:flex; align-items:center; justify-content:center;
                 font-size:1.8rem; box-shadow:0 2px 8px rgba(0,0,0,0.07);">🇯🇵</div>
            <div style="font-size:0.72rem; color:#888; margin-top:4px;">일본</div>
          </div>

          <!-- 미국 — 상단 우측 -->
          <div style="position:absolute; top:48px; right:120px; text-align:center;">
            <div style="width:52px; height:52px; background:#fff;
                 border:1px solid #eee; border-radius:50%;
                 display:flex; align-items:center; justify-content:center;
                 font-size:1.8rem; box-shadow:0 2px 8px rgba(0,0,0,0.07);">🇺🇸</div>
            <div style="font-size:0.72rem; color:#888; margin-top:4px;">미국</div>
          </div>

          <!-- 호주 — 중간 좌측 -->
          <div style="position:absolute; top:180px; left:30px; text-align:center;">
            <div style="width:60px; height:60px; background:#fff;
                 border:1px solid #eee; border-radius:50%;
                 display:flex; align-items:center; justify-content:center;
                 font-size:2rem; box-shadow:0 2px 8px rgba(0,0,0,0.07);">🇦🇺</div>
            <div style="font-size:0.72rem; color:#888; margin-top:4px;">호주</div>
          </div>

          <!-- 독일 — 중간 우측 -->
          <div style="position:absolute; top:195px; right:20px; text-align:center;">
            <div style="width:52px; height:52px; background:#fff;
                 border:1px solid #eee; border-radius:50%;
                 display:flex; align-items:center; justify-content:center;
                 font-size:1.8rem; box-shadow:0 2px 8px rgba(0,0,0,0.07);">🇩🇪</div>
            <div style="font-size:0.72rem; color:#888; margin-top:4px;">독일</div>
          </div>

          <!-- 캐나다 — 하단 좌측 -->
          <div style="position:absolute; bottom:60px; left:100px; text-align:center;">
            <div style="width:52px; height:52px; background:#fff;
                 border:1px solid #eee; border-radius:50%;
                 display:flex; align-items:center; justify-content:center;
                 font-size:1.8rem; box-shadow:0 2px 8px rgba(0,0,0,0.07);">🇨🇦</div>
            <div style="font-size:0.72rem; color:#888; margin-top:4px;">캐나다</div>
          </div>

          <!-- 한국 — 하단 우측 -->
          <div style="position:absolute; bottom:60px; right:100px; text-align:center;">
            <div style="width:52px; height:52px; background:#fff;
                 border:1px solid #eee; border-radius:50%;
                 display:flex; align-items:center; justify-content:center;
                 font-size:1.8rem; box-shadow:0 2px 8px rgba(0,0,0,0.07);">🇰🇷</div>
            <div style="font-size:0.72rem; color:#888; margin-top:4px;">한국</div>
          </div>

          <!-- 중앙 텍스트 -->
          <div style="position:absolute; top:50%; left:50%;
               transform:translate(-50%,-50%); text-align:center; width:300px;">
            <div style="font-size:0.72rem; font-weight:600; letter-spacing:0.12em;
                 color:#888; margin-bottom:0.9rem;">● YOUR NEXT CHAPTER</div>
            <h1 style="font-size:2rem; font-weight:800; color:#1a1a1a;
                 line-height:1.3; margin:0 0 0.75rem;">
              해외에서의 시작,<br>내 조건에 맞게.
            </h1>
            <p style="font-size:0.88rem; color:#888; line-height:1.6; margin:0 0 1.25rem;">
              나에게 맞는 비자·체류 프로그램을 비교하고,<br>
              필요한 서류와 준비할 일을 함께 알아보세요.
            </p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # CTA 버튼
    col1, col2, col3 = st.columns([2, 2, 2])
    with col2:
        if st.button("상담 시작하기  ↗", key="hero_cta", use_container_width=True, type="primary"):
            go_to(PAGE_CHAT)

    st.markdown("<div style='margin-top:2rem;'></div>", unsafe_allow_html=True)

    # ── 서비스 기능 카드 3개 ───────────────────────────────────
    features = [
        ("⊞", "나에게 맞는 프로그램 비교", "관심 있는 프로그램의 차이를 한눈에"),
        ("⟳", "내 조건에 맞는지 확인", "충족한 조건과 더 확인할 조건 정리"),
        ("≡", "준비할 일을 순서대로", "필요한 서류와 할 일을 체크리스트로"),
    ]
    cols = st.columns(3)
    for col, (icon, title, desc) in zip(cols, features):
        with col:
            st.markdown(
                f"""
                <div style="background:#fff; border:1px solid #f0f0f0;
                     border-radius:12px; padding:1.1rem 1.2rem;
                     display:flex; align-items:center; gap:0.9rem;
                     margin-bottom:0.5rem;">
                  <div style="font-size:1.2rem; color:#555; flex-shrink:0;">{icon}</div>
                  <div style="flex:1;">
                    <div style="font-size:0.88rem; font-weight:600;
                         color:#1a1a1a; margin-bottom:0.2rem;">{title}</div>
                    <div style="font-size:0.75rem; color:#aaa;">{desc}</div>
                  </div>
                  <div style="font-size:0.9rem; color:#ccc;">→</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── EXPLORE YOUR POSSIBILITIES ─────────────────────────────
    st.markdown("<div style='margin-top:3rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="text-align:center; padding:0 1rem;">
          <div style="font-size:0.7rem; font-weight:600; letter-spacing:0.12em;
               color:#aaa; margin-bottom:0.75rem;">EXPLORE YOUR POSSIBILITIES</div>
          <h2 style="font-size:1.7rem; font-weight:800; color:#1a1a1a;
               margin:0 0 0.75rem; line-height:1.3;">
            어디로 갈지 고민하는 순간부터.
          </h2>
          <p style="font-size:0.9rem; color:#888; line-height:1.6; margin:0 0 1.5rem;">
            국가나 목적을 아직 정하지 못했어도 괜찮아요.<br>
            일본·호주·미국·독일·캐나다에서의 시작을 함께 알아봐요.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 목적 pill 버튼
    p1, p2, p3, p4 = st.columns([1, 1, 2, 1])
    with p1:
        st.markdown(
            '<div style="display:flex; justify-content:flex-end;">'
            '<span style="display:inline-block; border:1.5px solid #e0e0e0;'
            ' border-radius:999px; padding:0.45rem 1.1rem; font-size:0.85rem;'
            ' color:#555; background:#fff;">🗂 취업</span></div>',
            unsafe_allow_html=True,
        )
    with p2:
        st.markdown(
            '<div style="display:flex; justify-content:center;">'
            '<span style="display:inline-block; border:1.5px solid #e0e0e0;'
            ' border-radius:999px; padding:0.45rem 1.1rem; font-size:0.85rem;'
            ' color:#555; background:#fff;">🎓 유학</span></div>',
            unsafe_allow_html=True,
        )
    with p3:
        st.markdown(
            '<div style="display:flex; justify-content:flex-start;">'
            '<span style="display:inline-block; border:1.5px solid #e0e0e0;'
            ' border-radius:999px; padding:0.45rem 1.1rem; font-size:0.85rem;'
            ' color:#555; background:#fff;">✈️ 워킹홀리데이 / 교류</span></div>',
            unsafe_allow_html=True,
        )

    # ── HOW IT WORKS ──────────────────────────────────────────
    st.markdown("<div style='margin-top:3rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="background:#f8f8f8; border-radius:16px;
             padding:2.5rem 2rem; margin-top:1rem;">
          <div style="text-align:center; margin-bottom:2rem;">
            <div style="font-size:0.7rem; font-weight:600; letter-spacing:0.12em;
                 color:#aaa; margin-bottom:0.6rem;">HOW IT WORKS</div>
            <h2 style="font-size:1.5rem; font-weight:800; color:#1a1a1a; margin:0;">
              궁금한 마음을, 준비하는 일상으로.
            </h2>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    steps = [
        ("01", "기본 정보 알려주기",
         "국적과 나이 등 간단한 정보를 입력해요. 관심 국가는 미정이어도 돼요."),
        ("02", "대화로 조건 알아보기",
         "원하는 활동을 이야기하고, 상담에 필요한 질문에 답해요."),
        ("03", "프로그램 비교하기",
         "관련 프로그램의 차이와 내 조건 검토 결과를 공식 출처와 함께 확인해요."),
        ("04", "준비할 일 확인하기",
         "서류와 절차, 관련 지원제도를 살펴보고 체크리스트로 준비해요."),
    ]
    cols = st.columns(4)
    for col, (num, title, desc) in zip(cols, steps):
        with col:
            st.markdown(
                f"""
                <div style="padding:0 0.5rem;">
                  <div style="font-size:1rem; font-weight:700; color:#bbb;
                       margin-bottom:0.5rem;">{num}</div>
                  <div style="font-size:0.88rem; font-weight:700; color:#1a1a1a;
                       margin-bottom:0.4rem;">{title}</div>
                  <div style="font-size:0.78rem; color:#999; line-height:1.6;">{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── 하단 여백 + 내 프로필 CTA ─────────────────────────────
    st.markdown("<div style='margin-top:2.5rem;'></div>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("👤  내 프로필 먼저 설정하기", key="profile_cta", use_container_width=True):
            go_to(PAGE_PROFILE)

    st.markdown(
        "<div style='text-align:center; font-size:0.72rem; color:#ccc;"
        " margin-top:3rem; padding-bottom:1rem;'>Global-In.</div>",
        unsafe_allow_html=True,
    )
