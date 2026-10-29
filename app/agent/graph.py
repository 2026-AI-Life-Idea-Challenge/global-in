"""상담 흐름 (LangGraph).

understand ─┬─(기본 정보 부족)→ ask ──────────────────────────→ END
            └─(충분)→ recommend ─┬─(후보 없음)→ END
                                  └→ eligibility(A) → prep_guide → END

대화 상태(프로필 등)는 checkpointer에 thread_id = session_id로 저장된다.
A·B는 지금 stubs.py 대역을 쓴다.
"""

from datetime import date

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from app.agent import preparation_planning, stubs, user_understanding
from app.agent.state import ConsultState
from app.models.user_profile import UserProfile


def build_graph(extractor: user_understanding.Extractor, checkpointer=None):
    def understand(state: ConsultState) -> ConsultState:
        profile = state.get("profile") or UserProfile()
        message = state.get("user_message")
        delta = extractor(message, profile) if message else None
        updates = {**(delta.updates() if delta else {}), **state.get("profile_updates", {})}
        profile, changed = user_understanding.merge_profile(profile, updates)
        return {
            "profile": profile,
            "changed_fields": changed,
            "intent": delta.intent if delta else "update_info",
            # 이번 턴 입력·이전 턴 결과가 다음 턴에 남지 않게 초기화
            "profile_updates": {},
            "follow_up_questions": [],
            "programs": [],
            "eligibility": [],
            "prep_items": [],
        }

    def ask(state: ConsultState) -> ConsultState:
        missing = user_understanding.missing_fields(state["profile"])
        return {
            "stage": "asking",
            "reply": "맞춤 상담을 위해 몇 가지만 알려주세요.",
            "follow_up_questions": user_understanding.follow_up_questions(missing),
        }

    def recommend(state: ConsultState) -> ConsultState:
        candidates = stubs.search_programs(state.get("user_message") or "", state["profile"])
        if not candidates:
            return {"stage": "result", "reply": "조건에 맞는 프로그램을 찾지 못했어요. 나라나 목적을 바꿔 보시겠어요?"}
        return {"programs": candidates}

    def check(state: ConsultState) -> ConsultState:
        ids = [p.program_id for p in state["programs"]]
        results = stubs.check_eligibility(state["profile"].to_evaluator_dict(), ids, as_of=date.today().isoformat())
        return {"eligibility": results}

    def guide(state: ConsultState) -> ConsultState:
        items = preparation_planning.build_prep_items(state["programs"], state["eligibility"], stubs.search_citations)
        return {
            "stage": "result",
            "reply": preparation_planning.build_reply(state["programs"], state["eligibility"], state["changed_fields"]),
            "prep_items": items,
        }

    graph = StateGraph(ConsultState)
    graph.add_node("understand", understand)
    graph.add_node("ask", ask)
    graph.add_node("recommend", recommend)
    graph.add_node("eligibility", check)
    graph.add_node("prep_guide", guide)

    graph.add_edge(START, "understand")
    graph.add_conditional_edges(
        "understand",
        lambda s: "ask" if user_understanding.missing_fields(s["profile"]) else "recommend",
    )
    graph.add_edge("ask", END)
    graph.add_conditional_edges("recommend", lambda s: "eligibility" if s.get("programs") else END)
    graph.add_edge("eligibility", "prep_guide")
    graph.add_edge("prep_guide", END)
    return graph.compile(checkpointer=checkpointer or InMemorySaver())
