# tools/technical_writer.py
from langchain_core.messages import HumanMessage
from langchain.chat_models.base import init_chat_model
import os

MODEL = "gpt-5"
llm = init_chat_model(MODEL, model_provider="openai")

def refine_document(content: str) -> str:
    """노션 콘텐츠를 기술문서 형태로 변환"""
    prompt = f"""
    아래 문서를 명확하고 간결한 기술 문서 스타일로 변환하세요:
    ---
    {content}
    ---
    """
    return llm.invoke([HumanMessage(content=prompt)]).content
