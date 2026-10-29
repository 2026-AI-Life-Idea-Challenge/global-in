"""
frontend/utils/session.py
세션 상태 초기화 및 관리 유틸리티
"""
import streamlit as st


# ── 페이지 상수 ─────────────────────────────────────────────────────────────
PAGE_HOME = "home"
PAGE_CHAT = "chat"
PAGE_PROGRAMS = "programs"
PAGE_PREPARATION = "preparation"
PAGE_PROFILE = "profile"


def init_session():
    """앱 최초 실행 시 세션 상태 기본값 설정."""

    if "saved_programs" not in st.session_state:
        st.session_state["saved_programs"] = {}

    # 현재 페이지
    if "page" not in st.session_state:
        st.session_state.page = PAGE_HOME

    # 사용자 프로필
    if "profile" not in st.session_state:
        st.session_state.profile = {
            "nationalities": [],
            "age": None,
            "residence_country": "",
            "education_level": "",
            "education_status": "",
            "major": "",
            "job_field": "",
            "career_duration": "",
            "languages": "",
            "language_certs": "",
            "target_countries": [],
            "undecided_country": True,
            "purposes": [],
            "undecided_purpose": True,
        }

    # 채팅 세션 목록
    if "chat_sessions" not in st.session_state:
        st.session_state.chat_sessions = []  # list of {id, title, messages}

    # 현재 채팅 세션 ID
    if "current_chat_id" not in st.session_state:
        st.session_state.current_chat_id = None

    # 프로그램 필터 상태
    if "program_filters" not in st.session_state:
        st.session_state.program_filters = {
            "tab": "전체",          # 전체 / 프로그램 / 지원제도
            "country": "전체",      # 전체 / 독일 / 일본 / 호주 / 미국 / 캐나다
            "purpose": "전체",      # 전체 / 취업 / 유학·교환학생 / 워킹홀리데이
            "keyword": "",
        }

    # 준비 체크리스트
    if "preparation_items" not in st.session_state:
        st.session_state.preparation_items = []  # list of checklist dicts


def go_to(page: str):
    """페이지 이동."""
    st.session_state.page = page
    st.rerun()


def get_profile() -> dict:
    return st.session_state.profile


def save_profile(data: dict):
    st.session_state.profile.update(data)


def new_chat_session(title: str = "새 채팅") -> str:
    """새 채팅 세션 생성, ID 반환."""
    import uuid
    session_id = str(uuid.uuid4())
    st.session_state.chat_sessions.append({
        "id": session_id,
        "title": title,
        "messages": [],
    })
    st.session_state.current_chat_id = session_id
    return session_id


def get_current_chat() -> dict | None:
    """현재 활성 채팅 세션 반환."""
    cid = st.session_state.current_chat_id
    if cid is None:
        return None
    for s in st.session_state.chat_sessions:
        if s["id"] == cid:
            return s
    return None


def append_message(role: str, content: str, extra: dict | None = None):
    """현재 채팅에 메시지 추가. role: 'user' | 'assistant'"""
    chat = get_current_chat()
    if chat is None:
        new_chat_session()
        chat = get_current_chat()
    msg = {"role": role, "content": content}
    if extra:
        msg.update(extra)
    chat["messages"].append(msg)
    # 채팅 제목을 첫 사용자 메시지로 자동 설정
    if role == "user" and chat["title"] == "새 채팅":
        chat["title"] = content[:20] + ("…" if len(content) > 20 else "")
