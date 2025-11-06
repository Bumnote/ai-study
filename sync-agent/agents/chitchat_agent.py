# agents/chitchat_agent.py
from langchain_core.messages import SystemMessage, HumanMessage
from langchain.chat_models.base import init_chat_model
from dotenv import load_dotenv
import os

load_dotenv()

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
chitchat_agent_llm = init_chat_model(MODEL, model_provider="openai")

CHITCHAT_SYSTEM = """당신은 친절하고 간결하게 대화하는 조수입니다.
- 프로젝트/문서와 무관한 일상 대화에 자연스럽게 응답하세요.
- 필요 시 1~2문장 정도의 추가 질문으로 대화를 이어가세요(과하지 않게).
"""

def chitchat_node(state):
    user_msg = state["messages"][-1].content
    result = chitchat_agent_llm.invoke([
        SystemMessage(content=CHITCHAT_SYSTEM),
        HumanMessage(content=user_msg),
    ])
    return {"answer": result.content}
