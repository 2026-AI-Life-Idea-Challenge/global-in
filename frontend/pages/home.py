"""
frontend/views/home.py
홈 화면 — 와이어프레임 완전 매칭
"""
import streamlit as st
from utils.session import go_to, PAGE_CHAT


def render():
    st.markdown(
        """
        <style>
        .block-container { padding:1rem 2rem !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ── HERO — 국가 코드 원형 배치 ────────────────────────────
    st.markdown(
        """
        <div style="position:relative; width:560px; height:520px;
             margin:2rem auto 0;">

          <!-- 외부 원 -->
          <div style="position:absolute; top:50%; left:50%;
               transform:translate(-50%,-50%);
               width:460px; height:460px;
               border:1px solid #e8e8e8; border-radius:50%;"></div>
          <!-- 내부 원 -->
          <div style="position:absolute; top:50%; left:50%;
               transform:translate(-50%,-50%);
               width:320px; height:320px;
               border:1px solid #eeeeee; border-radius:50%;"></div>

          <!-- JP 일본 — 상단 좌 -->
          <div style="position:absolute; top:36px; left:150px; text-align:center;">
            <div style="width:64px; height:64px; background:#fff;
                 border:1px solid #e4e4e4; border-radius:50%;
                 display:flex; align-items:center; justify-content:center;
                 font-size:1.25rem; font-weight:700; color:#1a1a1a;
                 box-shadow:0 2px 10px rgba(0,0,0,0.07);">JP</div>
            <div style="font-size:0.72rem; color:#999; margin-top:5px;">일본</div>
          </div>

          <!-- US 미국 — 상단 우 -->
          <div style="position:absolute; top:36px; right:136px; text-align:center;">
            <div style="width:64px; height:64px; background:#fff;
                 border:1px solid #e4e4e4; border-radius:50%;
                 display:flex; align-items:center; justify-content:center;
                 font-size:1.25rem; font-weight:700; color:#1a1a1a;
                 box-shadow:0 2px 10px rgba(0,0,0,0.07);">US</div>
            <div style="font-size:0.72rem; color:#999; margin-top:5px;">미국</div>
          </div>

          <!-- AU 호주 — 중간 좌 -->
          <div style="position:absolute; top:210px; left:16px; text-align:center;">
            <div style="width:64px; height:64px; background:#fff;
                 border:1px solid #e4e4e4; border-radius:50%;
                 display:flex; align-items:center; justify-content:center;
                 font-size:1.25rem; font-weight:700; color:#1a1a1a;
                 box-shadow:0 2px 10px rgba(0,0,0,0.07);">AU</div>
            <div style="font-size:0.72rem; color:#999; margin-top:5px;">호주</div>
          </div>

          <!-- DE 독일 — 중간 우 -->
          <div style="position:absolute; top:210px; right:10px; text-align:center;">
            <div style="width:64px; height:64px; background:#fff;
                 border:1px solid #e4e4e4; border-radius:50%;
                 display:flex; align-items:center; justify-content:center;
                 font-size:1.25rem; font-weight:700; color:#1a1a1a;
                 box-shadow:0 2px 10px rgba(0,0,0,0.07);">DE</div>
            <div style="font-size:0.72rem; color:#999; margin-top:5px;">독일</div>
          </div>

          <!-- CA 캐나다 — 하단 좌 -->
          <div style="position:absolute; bottom:36px; left:150px; text-align:center;">
            <div style="width:64px; height:64px; background:#fff;
                 border:1px solid #e4e4e4; border-radius:50%;
                 display:flex; align-items:center; justify-content:center;
                 font-size:1.25rem; font-weight:700; color:#1a1a1a;
                 box-shadow:0 2px 10px rgba(0,0,0,0.07);">CA</div>
            <div style="font-size:0.72rem; color:#999; margin-top:5px;">캐나다</div>
          </div>

          <!-- KR 한국 — 하단 우 -->
          <div style="position:absolute; bottom:36px; right:136px; text-align:center;">
            <div style="width:64px; height:64px; background:#fff;
                 border:1px solid #e4e4e4; border-radius:50%;
                 display:flex; align-items:center; justify-content:center;
                 font-size:1.25rem; font-weight:700; color:#1a1a1a;
                 box-shadow:0 2px 10px rgba(0,0,0,0.07);">KR</div>
            <div style="font-size:0.72rem; color:#999; margin-top:5px;">한국</div>
          </div>

          <!-- 중앙 텍스트 -->
          <div style="position:absolute; top:50%; left:50%;
               transform:translate(-50%,-50%); text-align:center; width:260px;">
            <div style="font-size:0.65rem; font-weight:700; letter-spacing:0.15em;
                 color:#aaa; margin-bottom:0.6rem;">● YOUR NEXT CHAPTER</div>
            <div style="font-size:1.85rem; font-weight:800; color:#1a1a1a;
                 line-height:1.25; margin-bottom:0.75rem;">
                해외에서의 시작,<br>내 조건에 맞게.
            </div>
            <div style="font-size:0.82rem; color:#888; line-height:1.6;">
                나에게 맞는 비자·체류 프로그램을 비교하고,<br>
                필요한 서류와 준비할 일을 함께 알아보세요.
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── CTA 버튼 ─────────────────────────────────────────────
    st.markdown("<div style='height:2rem;'></div>", unsafe_allow_html=True)
    col = st.columns([1, 2, 1])
    with col[1]:
        if st.button("상담 시작하기 ↗", key="home_cta", use_container_width=True, type="primary"):
            go_to(PAGE_CHAT)

    # ── 피처 카드 3개 ─────────────────────────────────────────
    st.markdown("<div style='height:2rem;'></div>", unsafe_allow_html=True)
    cards = [
        ("⊞", "나에게 맞는\n프로그램 비교", "관심 있는 프로그램의 차이를 한눈에"),
        ("◎", "내 조건에\n맞는지 확인", "충족한 조건과 더 갖춰야 할 것들"),
        ("≡", "준비할 일을\n순서대로", "필요한 서류와 할 일을 체크리스트로"),
    ]
    c1, c2, c3 = st.columns(3)
    for col, (icon, title, desc) in zip([c1, c2, c3], cards):
        with col:
            t = title.replace("\n", "<br>")
            st.markdown(
                f"""
                <div style="border:1px solid #ebebeb; border-radius:14px;
                     padding:1.25rem 1rem; background:#fff; min-height:130px;
                     display:flex; flex-direction:column; gap:0.4rem;">
                    <div style="font-size:0.95rem; font-weight:700;
                         color:#1a1a1a; line-height:1.35;">{t}</div>
                    <div style="font-size:0.75rem; color:#aaa; line-height:1.5;
                         flex:1;">{desc}</div>
                    <div style="text-align:right; font-size:0.8rem; color:#ccc;">→</div>
                    <div style="font-size:1.1rem; color:#bbb;">{icon}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── EXPLORE YOUR POSSIBILITIES ────────────────────────────
    st.markdown(
        """
        <div style="margin-top:3rem; margin-bottom:0.75rem;">
            <div style="font-size:0.65rem; font-weight:700; letter-spacing:0.15em;
                 color:#aaa; margin-bottom:0.5rem;">EXPLORE YOUR POSSIBILITIES</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    pill_cols = st.columns(3)
    for col, label in zip(pill_cols, ["워킹홀리데이 / 교류", "유학", "취업"]):
        with col:
            if st.button(label, key=f"home_pill_{label}", use_container_width=True):
                go_to(PAGE_CHAT)

    # ── HOW IT WORKS ──────────────────────────────────────────
    st.markdown(
        """
        <div style="background:#f8f8f8; border-radius:16px; padding:2rem 1.5rem;
             margin-top:3rem;">
            <div style="font-size:0.65rem; font-weight:700; letter-spacing:0.15em;
                 color:#aaa; margin-bottom:1.25rem;">HOW IT WORKS</div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:1.25rem;">
                <div>
                    <div style="font-size:0.65rem; color:#ccc; margin-bottom:0.25rem;">01</div>
                    <div style="font-size:0.88rem; font-weight:700; color:#1a1a1a;">기본 정보 알려주기</div>
                    <div style="font-size:0.75rem; color:#aaa; margin-top:0.2rem; line-height:1.5;">
                        나이, 학력, 목적 등 간단한 정보를 입력해요.</div>
                </div>
                <div>
                    <div style="font-size:0.65rem; color:#ccc; margin-bottom:0.25rem;">02</div>
                    <div style="font-size:0.88rem; font-weight:700; color:#1a1a1a;">대화로 조건 알아보기</div>
                    <div style="font-size:0.75rem; color:#aaa; margin-top:0.2rem; line-height:1.5;">
                        AI와 대화하며 내 상황에 맞는 조건을 파악해요.</div>
                </div>
                <div>
                    <div style="font-size:0.65rem; color:#ccc; margin-bottom:0.25rem;">03</div>
                    <div style="font-size:0.88rem; font-weight:700; color:#1a1a1a;">프로그램 비교하기</div>
                    <div style="font-size:0.75rem; color:#aaa; margin-top:0.2rem; line-height:1.5;">
                        맞춤 추천 프로그램을 조건별로 비교해요.</div>
                </div>
                <div>
                    <div style="font-size:0.65rem; color:#ccc; margin-bottom:0.25rem;">04</div>
                    <div style="font-size:0.88rem; font-weight:700; color:#1a1a1a;">준비할 일 확인하기</div>
                    <div style="font-size:0.75rem; color:#aaa; margin-top:0.2rem; line-height:1.5;">
                        서류·일정·체크리스트를 한 곳에서 관리해요.</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── 푸터 ─────────────────────────────────────────────────
    st.markdown(
        """
        <div style="text-align:center; padding:3rem 0 1rem;
             font-size:0.78rem; color:#ccc; font-weight:700; letter-spacing:0.1em;">
            Global-In.
        </div>
        """,
        unsafe_allow_html=True,
    )