# agents/supervisor_agent.py
import os
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.chat_models.base import init_chat_model

# ======================================
# ⚙️ 모델 초기화
# ======================================
MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1")
llm = init_chat_model(MODEL, model_provider="openai")

# ======================================
# 🧩 Pydantic Output Schema 정의
# ======================================
class SupervisorDecision(BaseModel):
    next_agent: str = Field(..., description="라우팅할 다음 에이전트 이름: rag, sync, chitchat 중 하나")
    reason: str = Field(..., description="선택 이유 요약")

# ======================================
# 🧠 Supervisor Prompt
# ======================================
SUPERVISOR_PROMPT = """
당신은 사용자 요청을 분석하여 아래 세 가지 중 어디로 보낼지 결정하는 Supervisor Agent입니다.

선택지는 다음과 같습니다:
1. "rag"  → 기존 문서에서 답변 가능한 질문
2. "sync" → 노션 등의 데이터 '동기화' 또는 '업데이트' 관련 요청
3. "chitchat" → 문서나 프로젝트와 무관한 일반 대화 (인사, 농담 등)

판단 기준:
- "회의록", "문서", "프로젝트" 등과 관련된 질문 → rag
- "동기화", "업데이트", "최신화", "갱신" 등의 단어 포함 → sync
- 그 외 개인적이거나 잡담성 대화 → chitchat
"""

# ======================================
# 🧭 Supervisor Node
# ======================================
def supervisor_node(state):
    """
    LangGraph용 Supervisor 노드 (Pydantic 기반)
    """
    user_msg = state["messages"][-1].content

    # ✅ 구조화된 출력 사용
    structured_llm = llm.with_structured_output(SupervisorDecision)
    decision = structured_llm.invoke([
        SystemMessage(content=SUPERVISOR_PROMPT),
        HumanMessage(content=user_msg)
    ])

    # ✅ 결과는 이미 Pydantic 모델로 검증된 상태
    return {
        "next_agent": decision.next_agent,
        "routing_context": {"reason": decision.reason},
        "sync_triggered": decision.next_agent == "sync",
    }
