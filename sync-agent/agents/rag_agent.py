# agents/rag_agent.py
"""
RAG Agent: Pinecone 검색 + LLM 요약 기반 답변 생성
"""

from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from utils.embeddings_pinecone import search_similar

# LLM 초기화
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.4)

def rag_agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pinecone 검색 + LLM 요약 기반 RAG 노드
    """
    query = state["messages"][-1].content
    print(f"🔍 [RAG] 사용자 질문: {query}")

    # 1️⃣ Pinecone 유사 문서 검색
    search_results = search_similar(query, top_k=5)
    if not search_results or len(search_results.get("matches", [])) == 0:
        return {"answer": "❌ 관련 문서를 찾을 수 없습니다."}

    # 2️⃣ 컨텍스트 구성
    contexts: List[str] = []
    for match in search_results["matches"]:
        meta = match["metadata"]
        contexts.append(
            f"제목: {meta.get('title')}\n유형: {meta.get('type')}\n내용: {meta.get('text', '')}"
        )

    context_text = "\n\n".join(contexts[:3])

    # 3️⃣ LLM에 질의 (검색된 문서를 기반으로 답변 생성)
    prompt = f"""
    당신은 회사 회의록 및 기술 문서를 기반으로 질문에 답변하는 AI 어시스턴트입니다.
    아래는 관련 문서들의 요약입니다. 이 내용을 참고하여 질문에 구체적으로 답변하세요.

    [관련 문서]
    {context_text}

    [사용자 질문]
    {query}

    [출력 형식]
    - 요약된 문장으로 답변
    - 근거가 되는 문서 제목 목록 포함
    """

    result = llm.invoke(prompt)

    return {
        "answer": result.content,
        "query": query,
        "references": [m["metadata"]["title"] for m in search_results["matches"]],
    }
