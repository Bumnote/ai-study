# agents/sync_agent.py
"""
Notion → 문서 분류 → 임베딩 저장(Pinecone)
LangGraph 노드로 통합 가능한 Sync Agent
"""

import os, asyncio
from typing import Dict, Any, List
from datetime import datetime
from utils.notion_client import NotionClient
from utils.document_classifier import classify_document
from utils.embeddings_pinecone import embed_and_store

def sync_agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
    print("🚀 [SyncAgent] 노션 데이터 동기화 시작")
    notion = NotionClient()

    all_pages = notion.fetch_all_pages()
    print(f"📄 {len(all_pages)}개 페이지 발견")

    synced_pages: List[str] = []
    failed_pages: List[str] = []

    for p in all_pages:
        page_id = p["id"]
        title = p.get("title", "(제목 없음)")
        url = p.get("url", "")
        last_edited_time = p.get("last_edited_time", "")
        print(f"🔍 [{title}] (id={page_id}) 처리 중...")

        try:
            # 1️⃣ 페이지 본문 가져오기
            content = notion.fetch_page_content(page_id)
            if not content.strip():
                print(f"⚠️ [{title}] 내용이 비어있음, 건너뜀")
                continue

            # 2️⃣ 문서 타입 분류
            result = classify_document({"text": content, "file_path": title})
            doc_type = result.get("doc_type", "미분류")
            print(f"📝 분류 결과: {doc_type}")

            # 3️⃣ Pinecone 저장용 문서 객체 생성
            doc = {
                "title": title,
                "doc_type": doc_type,
                "summary": content,  # 또는 result.get("summary", content)
                "source": "notion",
                "last_edited_time": last_edited_time,
                "url": url
            }

            # 4️⃣ Pinecone에 저장
            embed_and_store(doc)

            print(f"✅ [{title}] 동기화 완료 ({doc_type})")
            synced_pages.append(f"{title} ({doc_type})")

        except Exception as e:
            print(f"❌ [{title}] 오류 발생: {e}")
            failed_pages.append(title)

    print("🧾 동기화 완료 요약:")
    print(f" - 성공: {len(synced_pages)}개")
    print(f" - 실패: {len(failed_pages)}개")

    return {
        "last_synced_at": datetime.now().isoformat(),
        "synced_pages": synced_pages,
        "failed_pages": failed_pages,
        "sync_count": len(synced_pages),
    }
