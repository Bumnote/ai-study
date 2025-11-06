# graph.py
import os
from typing import Literal, TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage

# ↙ 이미 작성하신 Supervisor를 재사용 (Pydantic 구조화 출력 기반 권장)
from agents.supervisor_agent import supervisor_node   # next_agent: rag|sync|chitchat
from agents.rag_agent import rag_node
from agents.sync_agent import sync_node
from agents.chitchat_agent import chitchat_node

# =========================
# 1) State 정의
# =========================
class RouterState(TypedDict):
    messages: Annotated[list, add_messages]
    next_agent: Literal["rag", "sync", "chitchat"]
    routing_context: dict
    sync_triggered: bool
    # Agent outputs
    answer: str
    rag_context: list
    sync_result: dict
    # Optional inputs
    query: str
    sync_params: dict

# =========================
# 2) 그래프 빌더
# =========================
def build_graph(retriever=None, sync_fn=None):
    """
    retriever: Optional[BaseRetriever]  (RAG 검색기)
    sync_fn: Optional[Callable]         (동기화 실행 함수)

    반환: RunnableGraph
    """
    graph = StateGraph(RouterState)

    # ---- 노드 추가
    graph.add_node("supervisor", supervisor_node)
    # DI가 필요한 노드는 래핑
    if retriever is None:
        graph.add_node("rag", rag_node)
    else:
        # partial 적용 없이 람다로 감싸 DI
        def _rag(state):
            return rag_node(state, retriever=retriever)
        graph.add_node("rag", _rag)

    if sync_fn is None:
        graph.add_node("sync", sync_node)
    else:
        def _sync(state):
            return sync_node(state, sync_fn=sync_fn)
        graph.add_node("sync", _sync)

    graph.add_node("chitchat", chitchat_node)

    # ---- 엣지 연결
    graph.add_edge(START, "supervisor")

    def route(state: RouterState) -> str:
        # supervisor가 설정한 next_agent로 분기
        nxt = state.get("next_agent", "rag")
        if nxt not in ("rag", "sync", "chitchat"):
            return "rag"
        return nxt

    graph.add_conditional_edges(
        "supervisor",
        route,
        {
            "rag": "rag",
            "sync": "sync",
            "chitchat": "chitchat",
        },
    )

    # 각 노드 종료
    graph.add_edge("rag", END)
    graph.add_edge("sync", END)
    graph.add_edge("chitchat", END)

    return graph.compile()

# =========================
# 3) 간단 실행 예시 (로컬 테스트)
# =========================
if __name__ == "__main__":
    # 예시용 더미 retriever/sync
    class DummyRetriever:
        def get_relevant_documents(self, q):
            from langchain.docstore.document import Document
            return [Document(page_content=f"Dummy context for: {q}")]

    def dummy_sync_fn(params=None):
        return {"ok": True, "synced": 7, "source": "notion", "details": "delta-upsert"}

    app = build_graph(retriever=DummyRetriever(), sync_fn=dummy_sync_fn)

    # 1) 문서 기반 질문
    out = app.invoke({"messages": [HumanMessage("회의록에서 백로그 결정사항 요약해줘")]} )
    print("\n[RAG] >", out.get("answer"))

    # 2) 동기화 요청
    out = app.invoke({"messages": [HumanMessage("노션 데이터 최신으로 동기화해줘")], "sync_params": {"target": "notion"}})
    print("\n[SYNC] >", out.get("answer"))

    # 3) 일상 대화
    out = app.invoke({"messages": [HumanMessage("요즘 날씨가 쌀쌀하네?")]})
    print("\n[CHITCHAT] >", out.get("answer"))
