# agent_factory.py
import os
import asyncio
from typing import Any, Dict, Optional, List

from dotenv import load_dotenv
load_dotenv(override=True)

from langgraph.checkpoint.memory import MemorySaver
from langchain_core.runnables import RunnableConfig
from langchain.chat_models.base import init_chat_model
from langchain.agents import create_agent

from prompt_router import route_prompt
from tools import get_tools_for_context, all_tools as LOCAL_TOOLS


# ============================================================
# 🧠 1. Dynamic Agent Factory
# ============================================================
async def create_dynamic_agent(
    user_input: str,
    checkpointer: Optional[MemorySaver] = None,
    thread_id: Optional[str] = None
):
    """
    1. 사용자 입력 분석 (prompt_router)
    2. 컨텍스트에 맞는 in-process FastMCP 도구 선택
    3. LangGraph ReAct Agent 생성 및 반환
    
    Returns:
        (agent, client, routing_info)
        - agent: LangGraph Agent Graph
        - client: 항상 None (in-process 사용)
        - routing_info: {"context": str, "servers": List[str], "error": Optional[str]}
    """
    routing = route_prompt(user_input)
    context = routing["context"]
    contexts = routing.get("contexts", [context])  # 복합 컨텍스트 지원
    system_prompt = routing["prompt"]

    print(f"🔍 감지된 Context: {contexts}")

    # In-process 도구 선택 (복합 컨텍스트 지원)
    tools = get_tools_for_context(contexts)
    connected_servers = [f"inprocess:{c}" for c in contexts] if tools else []
    error_msg = None

    if not tools:
        print("⚠️ 사용 가능한 도구가 없습니다. 기본 대화 모드로 계속합니다.")

    MODEL_NAME = os.getenv("OPENAI_MODEL", os.getenv("MODEL_NAME", "gpt-5"))
    MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "openai")
    model = init_chat_model(MODEL_NAME, model_provider=MODEL_PROVIDER)
    cp = checkpointer or MemorySaver()
    
    # ✅ Agent 생성 시 명시적 설정
    # ✅ Agent 생성 시 recursion_limit 증가
    agent = create_agent(
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        checkpointer=cp,
    )

    routing_info = {
        "context": context,
        "contexts": contexts,
        "servers": connected_servers,
        "error": error_msg
    }

    return agent, None, routing_info


# ============================================================
# 🧠 2. 실행 래퍼 (단일 질의 실행)
# ============================================================
async def run_dynamic_agent(
    user_input: str,
    checkpointer: Optional[MemorySaver] = None,
    thread_id: Optional[str] = "default"
):
    """
    주어진 사용자 입력을 기반으로 동적으로 에이전트를 생성하고 실행합니다.
    """
    agent, _, routing_info = await create_dynamic_agent(
        user_input, 
        checkpointer=checkpointer, 
        thread_id=thread_id
    )

    try:
        print(f"\n🧩 실행 요청: {user_input}")
        print(f"📍 라우팅: {routing_info}\n")

        inputs = {"messages": [{"role": "user", "content": user_input}]}
        # ✅ recursion_limit 설정 추가
        config = {
            "configurable": {"thread_id": thread_id or "default"},
            "recursion_limit": 50  # 25 → 50으로 증가
        }
        
        async for chunk in agent.astream(inputs, config=config, stream_mode="updates"):
            print(f"[CHUNK] {chunk}")

    finally:
        pass
