"""
✅ 수정 완료 버전
Supervisor Agent - 최상위 라우팅 및 조율 에이전트
LangGraph + Subgraph 구조 호환 완전판
"""

import os
from typing import Literal, TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.chat_models.base import init_chat_model
from dotenv import load_dotenv

load_dotenv()

# ============================================================
# State 정의
# ============================================================
class SupervisorState(TypedDict):
    """Supervisor Agent의 상태"""
    messages: Annotated[list, add_messages]
    next_agent: str  # "rag_agent", "mcp_create_agent", "sync_agent", "final"
    routing_context: dict  # 라우팅 정보
    sync_triggered: bool  # 동기화 트리거 여부


# ============================================================
# Supervisor Agent
# ============================================================
SUPERVISOR_PROMPT = """당신은 사용자 요청을 분석하고 적절한 전문 에이전트로 라우팅하는 Supervisor Agent입니다.

**사용 가능한 에이전트:**
1. **rag_agent**: 기존 문서 검색 및 질의응답
   - "지난주 회의 내용 찾아줘"
   - "프로젝트 문서에서 XXX 검색"
   - "이전에 논의한 내용 알려줘"

2. **mcp_create_agent**: 새 문서 생성, 코드 분석, 메시지 전송
   - "회의록 작성해줘"
   - "GitHub 저장소 분석해줘"
   - "Discord에 메시지 보내줘"
   - "기술 회고 작성해줘"

3. **sync_agent**: Notion 동기화
   - "Notion 동기화해줘"
   - "최신 페이지 가져와줘"
   - "동기화 상태 확인해줘"
   - "전체 동기화 실행해줘"

**라우팅 규칙:**
- 기존 문서 검색/조회 → rag_agent
- 새 문서 생성/수정, 외부 도구 사용 → mcp_create_agent
- 동기화 요청 → sync_agent
- 간단한 질문/대화 → final (직접 응답)

**응답 형식:**
다음 중 하나를 반환하세요: "rag_agent", "mcp_create_agent", "sync_agent", "final"
"""

def create_supervisor_agent():
    """Supervisor Agent (라우팅만 수행하는 경량 그래프)"""
    
    model = init_chat_model(
        os.getenv("OPENAI_MODEL", "gpt-4o"),
        model_provider=os.getenv("MODEL_PROVIDER", "openai")
    )
    
    # 사용자 요청 분석
    def analyze_request(state: SupervisorState) -> SupervisorState:
        messages = state["messages"]
        last_message = messages[-1].content if messages else ""
        
        routing_prompt = f"""{SUPERVISOR_PROMPT}

사용자 요청: {last_message}

이 요청을 처리할 에이전트를 선택하세요: rag_agent, mcp_create_agent, sync_agent, final"""
        
        response = model.invoke([SystemMessage(content=routing_prompt)])
        next_agent = response.content.strip().lower()
        
        valid_agents = ["rag_agent", "mcp_create_agent", "sync_agent", "final"]
        if next_agent not in valid_agents:
            text = last_message.lower()
            if any(k in text for k in ["동기화", "sync", "최신", "가져와"]):
                next_agent = "sync_agent"
            elif any(k in text for k in ["찾아", "검색", "조회", "알려줘"]):
                next_agent = "rag_agent"
            elif any(k in text for k in ["작성", "생성", "만들어", "분석", "보내"]):
                next_agent = "mcp_create_agent"
            else:
                next_agent = "final"
        
        print(f"🎯 Supervisor 라우팅 결정 → {next_agent}")
        
        return {
            **state,
            "next_agent": next_agent,
            "routing_context": {
                "original_request": last_message,
                "selected_agent": next_agent
            }
        }

    # 간단한 대화 응답 노드
    def final_response(state: SupervisorState) -> SupervisorState:
        messages = state["messages"]
        last_message = messages[-1].content if messages else ""
        
        response = model.invoke([
            SystemMessage(content="당신은 친절한 AI 어시스턴트입니다. 한국어로 답변하세요."),
            HumanMessage(content=last_message)
        ])
        
        return {
            **state,
            "messages": [AIMessage(content=response.content)],
            "next_agent": "final"
        }

    # Supervisor 내부 그래프 (라우팅만 담당)
    workflow = StateGraph(SupervisorState)
    workflow.add_node("analyze", analyze_request)
    workflow.add_node("final", final_response)
    
    # 단순 경로만 정의 (라우팅 결과는 state에 담김)
    workflow.add_edge(START, "analyze")
    workflow.add_edge("analyze", "final")
    workflow.add_edge("final", END)
    
    return workflow.compile()


# ============================================================
# 통합 Agent Factory
# ============================================================
def create_integrated_agent_with_supervisor():
    """
    Supervisor + 전문 에이전트 통합 그래프
    """
    from agent_factory import create_dynamic_agent
    from sync_tools import (
        check_sync_status,
        full_sync_notion,
        incremental_sync_notion,
        auto_sync_after_notion_action
    )

    # Supervisor 서브그래프
    supervisor = create_supervisor_agent()

    # ---------------------------
    # 각 에이전트 노드 정의
    # ---------------------------
    async def rag_agent_node(state: SupervisorState) -> SupervisorState:
        """RAG 검색"""
        print("📚 RAG Agent 실행 중...")
        return {
            **state,
            "messages": [AIMessage(content="RAG Agent: 문서 검색 결과입니다. (구현 필요)")],
            "next_agent": "final"
        }

    async def mcp_create_agent_node(state: SupervisorState) -> SupervisorState:
        """MCP Create Agent"""
        print("🛠️ MCP Create Agent 실행 중...")
        messages = state["messages"]
        last_message = messages[-1].content if messages else ""

        agent, _, routing_info = await create_dynamic_agent(last_message)
        inputs = {"messages": [{"role": "user", "content": last_message}]}
        config = {"configurable": {"thread_id": "supervisor_thread"}}

        result_messages = []
        async for chunk in agent.astream(inputs, config=config, stream_mode="values"):
            if "messages" in chunk:
                result_messages = chunk["messages"]

        should_sync = "notion" in routing_info.get("contexts", [])
        response_content = result_messages[-1].content if result_messages else "작업 완료"

        return {
            **state,
            "messages": [AIMessage(content=response_content)],
            "sync_triggered": should_sync,
            "next_agent": "auto_sync" if should_sync else "final"
        }

    async def sync_agent_node(state: SupervisorState) -> SupervisorState:
        """Sync Agent"""
        print("🔄 Sync Agent 실행 중...")
        messages = state["messages"]
        last_message = messages[-1].content if messages else ""
        text = last_message.lower()

        if "전체" in text or "full" in text:
            result = await full_sync_notion()
        elif "상태" in text or "status" in text:
            result = await check_sync_status()
        else:
            result = await incremental_sync_notion()

        if result.get("success"):
            response = f"""✅ 동기화 완료!

📊 결과:
- 새 페이지: {result.get('new_count', 0)}개
- 업데이트: {result.get('updated_count', 0)}개
- 총 임베딩: {result.get('total_embeddings', 0)}개

{result.get('message', '')}"""
        else:
            response = f"❌ 동기화 실패: {result.get('error', '알 수 없는 오류')}"

        return {
            **state,
            "messages": [AIMessage(content=response)],
            "next_agent": "final"
        }

    async def auto_sync_node(state: SupervisorState) -> SupervisorState:
        """자동 동기화"""
        print("⚡ 자동 동기화 실행 중...")
        result = await auto_sync_after_notion_action()
        messages = state["messages"]
        last_message = messages[-1].content if messages else ""

        sync_info = f"\n\n🔄 자동 동기화: {result.get('new_count', 0)}개 새로 추가, {result.get('updated_count', 0)}개 업데이트됨"
        updated_message = AIMessage(content=last_message + sync_info)

        return {
            **state,
            "messages": [updated_message],
            "next_agent": "final"
        }

    # ---------------------------
    # 통합 그래프 구성
    # ---------------------------
    workflow = StateGraph(SupervisorState)

    # 노드 등록
    workflow.add_node("supervisor", supervisor)
    workflow.add_node("rag_agent", rag_agent_node)
    workflow.add_node("mcp_create_agent", mcp_create_agent_node)
    workflow.add_node("sync_agent", sync_agent_node)
    workflow.add_node("auto_sync", auto_sync_node)

    # 엣지 연결
    workflow.add_edge(START, "supervisor")

    # Supervisor → 각 에이전트 라우팅
    workflow.add_conditional_edges(
        "supervisor",
        lambda s: s["next_agent"],
        {
            "rag_agent": "rag_agent",
            "mcp_create_agent": "mcp_create_agent",
            "sync_agent": "sync_agent",
            "final": END
        }
    )

    # MCP 실행 후 후속 처리
    workflow.add_conditional_edges(
        "mcp_create_agent",
        lambda s: s["next_agent"],
        {
            "auto_sync": "auto_sync",
            "final": END
        }
    )

    workflow.add_edge("rag_agent", END)
    workflow.add_edge("sync_agent", END)
    workflow.add_edge("auto_sync", END)

    return workflow.compile()
