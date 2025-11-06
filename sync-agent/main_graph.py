# ============================================================
# main_graph.py - 통합 LangGraph 워크플로우
# ============================================================
import os
from typing import TypedDict, Literal, List, Dict, Any
from datetime import datetime
from pathlib import Path

from langchain.chat_models.base import init_chat_model
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import PromptTemplate
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from dotenv import load_dotenv

load_dotenv()

# ============================================================
# State Definition
# ============================================================
class GraphState(TypedDict):
    messages: List[Any]
    next_agent: str
    routing_context: Dict[str, Any]
    sync_triggered: bool
    synced_pages: List[Dict[str, Any]]
    failed_pages: List[str]
    last_synced_at: str


# ============================================================
# 1️⃣ Supervisor Agent
# ============================================================
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
llm = init_chat_model(MODEL, model_provider="openai")

class SupervisorDecision(BaseModel):
    next_agent: str = Field(..., description="라우팅할 다음 에이전트: rag, sync, chitchat")
    reason: str = Field(..., description="선택 이유")

SUPERVISOR_PROMPT = """
당신은 사용자 요청을 분석하여 적절한 에이전트로 라우팅하는 Supervisor입니다.

선택지:
1. "rag" → 기존 문서에서 답변 가능한 질문
2. "sync" → 노션 데이터 동기화/업데이트 요청
3. "chitchat" → 일반 대화

판단 기준:
- "동기화", "업데이트", "최신화", "갱신" → sync
- "회의록", "문서", "프로젝트" 관련 질문 → rag
- 그 외 → chitchat
"""

def supervisor_node(state: GraphState) -> GraphState:
    """Supervisor: 사용자 요청을 분석하여 라우팅"""
    print("\n" + "="*70)
    print("🧭 [SUPERVISOR] 요청 분석 중...")
    print("="*70)
    
    user_msg = state["messages"][-1].content
    
    structured_llm = llm.with_structured_output(SupervisorDecision)
    decision = structured_llm.invoke([
        SystemMessage(content=SUPERVISOR_PROMPT),
        HumanMessage(content=user_msg)
    ])
    
    print(f"📍 라우팅 결정: {decision.next_agent}")
    print(f"📝 이유: {decision.reason}\n")
    
    return {
        **state,
        "next_agent": decision.next_agent,
        "routing_context": {"reason": decision.reason},
        "sync_triggered": decision.next_agent == "sync",
    }


# ============================================================
# 2️⃣ Sync Agent (Notion → Technical Writing → DB/Vector)
# ============================================================
from utils.notion_client import NotionClient
from utils.document_classifier import classify_document
from utils.embeddings_pinecone import embed_and_store
import mysql.connector
from mysql.connector import Error

def save_to_mysql(page_data: Dict[str, Any], technical_content: str) -> bool:
    """MySQL에 문서 저장"""
    db_config = {
        'host': os.getenv('MYSQL_HOST', 'localhost'),
        'port': int(os.getenv('MYSQL_PORT', 3306)),
        'user': os.getenv('MYSQL_USER', 'root'),
        'password': os.getenv('MYSQL_PASSWORD'),
        'database': os.getenv('MYSQL_DATABASE', 'notion_db')
    }
    
    try:
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        
        # 테이블 생성
        create_table_query = """
        CREATE TABLE IF NOT EXISTS notion_documents (
            page_id VARCHAR(36) PRIMARY KEY,
            title VARCHAR(500),
            doc_type VARCHAR(50),
            original_content TEXT,
            technical_content TEXT,
            url TEXT,
            last_edited_time VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_doc_type (doc_type),
            INDEX idx_title (title(100))
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        cursor.execute(create_table_query)
        
        # 데이터 삽입/업데이트
        insert_query = """
        INSERT INTO notion_documents 
        (page_id, title, doc_type, original_content, technical_content, url, last_edited_time)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            title = VALUES(title),
            doc_type = VALUES(doc_type),
            original_content = VALUES(original_content),
            technical_content = VALUES(technical_content),
            url = VALUES(url),
            last_edited_time = VALUES(last_edited_time),
            updated_at = CURRENT_TIMESTAMP
        """
        
        values = (
            page_data["page_id"],
            page_data["title"],
            page_data["doc_type"],
            page_data["original_content"],
            technical_content,
            page_data["url"],
            page_data["last_edited_time"]
        )
        
        cursor.execute(insert_query, values)
        conn.commit()
        
        cursor.close()
        conn.close()
        return True
        
    except Error as e:
        print(f"❌ MySQL 저장 실패: {e}")
        return False


def apply_technical_writing(content: str, doc_type: str, title: str) -> str:
    """문서 타입에 맞는 Technical Writing 적용"""
    template_map = {
        "회의록": "./templates/meeting_template.txt",
        "기술 회의": "./templates/tech_review_template.txt",
        "회고록": "./templates/retrospective_template.txt"
    }
    
    template_path = template_map.get(doc_type)
    
    # 템플릿이 없으면 원본 반환
    if not template_path or not Path(template_path).exists():
        print(f"⚠️  템플릿 없음, 원본 사용")
        return content
    
    # 템플릿 로드
    with open(template_path, "r", encoding="utf-8") as f:
        template_str = f.read()
    
    prompt = PromptTemplate(input_variables=["context"], template=template_str)
    formatted_prompt = prompt.format(context=content)
    
    result = llm.invoke(formatted_prompt)
    return result.content


def save_as_markdown(title: str, doc_type: str, content: str) -> str:
    """MD 파일로 저장"""
    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    
    safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
    filename = f"{safe_title}_{doc_type}_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    file_path = output_dir / filename
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    return str(file_path)


def sync_agent_node(state: GraphState) -> GraphState:
    """Sync Agent: Notion → 분류 → Technical Writing → DB/Vector 저장"""
    print("\n" + "="*70)
    print("🔄 [SYNC AGENT] Notion 동기화 시작")
    print("="*70)
    
    notion = NotionClient()
    all_pages = notion.fetch_all_pages()
    
    print(f"📄 총 {len(all_pages)}개 페이지 발견\n")
    
    synced_pages = []
    failed_pages = []
    
    for page in all_pages:
        page_id = page["id"]
        title = page.get("title", "(제목 없음)")
        url = page.get("url", "")
        last_edited = page.get("last_edited_time", "")
        
        print(f"🔍 처리 중: [{title}]")
        
        try:
            # 1️⃣ 페이지 콘텐츠 가져오기
            content = notion.fetch_page_content(page_id)
            
            if not content.strip():
                print(f"   ⚠️  내용 없음, 건너뜀\n")
                continue
            
            # 2️⃣ 문서 분류
            classification_result = classify_document({
                "text": content,
                "file_path": title
            })
            doc_type = classification_result.get("doc_type", "미분류")
            print(f"   📝 분류: {doc_type}")
            
            # 3️⃣ Technical Writing 적용
            print(f"   ✍️  Technical Writing 적용 중...")
            technical_content = apply_technical_writing(content, doc_type, title)
            
            # 4️⃣ MD 파일 저장
            md_path = save_as_markdown(title, doc_type, technical_content)
            print(f"   📁 MD 저장: {md_path}")
            
            # 5️⃣ MySQL 저장
            page_data = {
                "page_id": page_id,
                "title": title,
                "doc_type": doc_type,
                "original_content": content,
                "url": url,
                "last_edited_time": last_edited
            }
            
            mysql_success = save_to_mysql(page_data, technical_content)
            if mysql_success:
                print(f"   💾 MySQL 저장 완료")
            
            # 6️⃣ Pinecone 임베딩 저장
            doc_for_embedding = {
                "page_id": page_id,
                "title": title,
                "doc_type": doc_type,
                "summary": technical_content,  # Technical Writing 적용된 내용 사용
                "source": "notion",
                "last_edited_time": last_edited,
                "url": url
            }
            
            embed_result = embed_and_store(doc_for_embedding)
            if embed_result:
                print(f"   🔢 Pinecone 저장 완료 ({embed_result['chunks']}개 청크)")
            
            synced_pages.append({
                "title": title,
                "doc_type": doc_type,
                "page_id": page_id,
                "md_path": md_path
            })
            
            print(f"   ✅ 완료\n")
            
        except Exception as e:
            print(f"   ❌ 오류: {e}\n")
            failed_pages.append(title)
    
    print("="*70)
    print(f"🎉 동기화 완료: 성공 {len(synced_pages)}개 / 실패 {len(failed_pages)}개")
    print("="*70 + "\n")
    
    # 응답 메시지 생성
    response_msg = f"""✅ **동기화 완료**

📊 **결과 요약**
- 성공: {len(synced_pages)}개
- 실패: {len(failed_pages)}개

📝 **처리된 문서**
"""
    
    for page in synced_pages[:10]:  # 최대 10개만 표시
        response_msg += f"\n- {page['title']} ({page['doc_type']})"
    
    if len(synced_pages) > 10:
        response_msg += f"\n... 외 {len(synced_pages) - 10}개"
    
    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=response_msg)],
        "synced_pages": synced_pages,
        "failed_pages": failed_pages,
        "last_synced_at": datetime.now().isoformat()
    }


# ============================================================
# 3️⃣ RAG Agent (기존 문서 검색)
# ============================================================
def rag_agent_node(state: GraphState) -> GraphState:
    """RAG Agent: Pinecone에서 검색하여 답변"""
    print("\n" + "="*70)
    print("🔍 [RAG AGENT] 문서 검색 중...")
    print("="*70)
    
    # TODO: Pinecone 검색 + LLM 답변 생성 로직
    response = "RAG 에이전트 응답 (구현 예정)"
    
    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=response)]
    }


# ============================================================
# 4️⃣ Chitchat Agent
# ============================================================
def chitchat_agent_node(state: GraphState) -> GraphState:
    """Chitchat Agent: 일반 대화"""
    print("\n" + "="*70)
    print("💬 [CHITCHAT AGENT] 일반 대화")
    print("="*70)
    
    user_msg = state["messages"][-1].content
    response = llm.invoke([HumanMessage(content=user_msg)])
    
    return {
        **state,
        "messages": state["messages"] + [AIMessage(content=response.content)]
    }


# ============================================================
# 5️⃣ Build Graph
# ============================================================
def route_after_supervisor(state: GraphState) -> Literal["sync", "rag", "chitchat"]:
    """Supervisor 결정에 따라 라우팅"""
    return state["next_agent"]


def build_graph():
    """LangGraph 워크플로우 구성"""
    workflow = StateGraph(GraphState)
    
    # 노드 추가
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("sync", sync_agent_node)
    workflow.add_node("rag", rag_agent_node)
    workflow.add_node("chitchat", chitchat_agent_node)
    
    # Supervisor → 조건부 라우팅
    workflow.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "sync": "sync",
            "rag": "rag",
            "chitchat": "chitchat"
        }
    )
    
    # 각 에이전트 → END
    workflow.add_edge("sync", END)
    workflow.add_edge("rag", END)
    workflow.add_edge("chitchat", END)
    
    # 시작점
    workflow.set_entry_point("supervisor")
    
    return workflow.compile()


# ============================================================
# 6️⃣ Main Execution
# ============================================================
def main():
    """메인 실행 함수"""
    app = build_graph()
    
    print("\n" + "🤖 " + "="*66)
    print("  Notion Document Processing System")
    print("  - Supervisor: 요청 분석 및 라우팅")
    print("  - Sync Agent: Notion → Technical Writing → DB/Vector")
    print("  - RAG Agent: 문서 검색 및 답변")
    print("  - Chitchat Agent: 일반 대화")
    print("="*70 + "\n")
    
    # 테스트 실행
    initial_state = {
        "messages": [HumanMessage(content="노션 문서를 동기화해주세요")],
        "next_agent": "",
        "routing_context": {},
        "sync_triggered": False,
        "synced_pages": [],
        "failed_pages": [],
        "last_synced_at": ""
    }
    
    result = app.invoke(initial_state)
    
    print("\n" + "="*70)
    print("✅ 처리 완료")
    print("="*70)
    print(f"\n최종 응답:\n{result['messages'][-1].content}")


if __name__ == "__main__":
    main()