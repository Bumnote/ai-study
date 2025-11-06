# tools/vector_store.py
"""
Notion 페이지를 Pinecone VectorStore에 임베딩 저장하는 래퍼 모듈
(embeddings_pinecone.py 의 embed_and_store()를 활용)
"""

import os
from utils.embeddings_pinecone import embed_and_store 

def embed_and_store_page(
    page_id: str,
    page_url: str,
    md_text: str,
    title: str = "Untitled",
    doc_type: str = "미분류"
):
    """
    ✅ Notion 페이지를 Pinecone VectorStore에 임베딩하고 저장합니다.

    Args:
        page_id (str): Notion 페이지 ID
        page_url (str): Notion 페이지 URL
        md_text (str): 페이지의 마크다운 텍스트 내용
        title (str): 문서 제목
        doc_type (str): 문서 타입 (회의록 / 기술 회의 / 회고록 등)
    Returns:
        bool: 저장 성공 여부
    """

    # 🔹 환경변수에서 동기화 시간 가져오기
    last_sync_time = os.getenv("CURRENT_SYNC_TIME", "unknown")

    # 🔹 Pinecone에 업서트할 문서 데이터 구성
    doc = {
        "title": title,
        "doc_type": doc_type,
        "summary": md_text[:4000],  # OpenAI embedding 입력 제한 내 일부 사용
        "source": "notion",
        "last_edited_time": last_sync_time,
        "url": page_url,
        "page_id": page_id  # ✅ 추가: 추적 가능하도록 page_id 메타 포함
    }

    print(f"📦 [VECTOR_STORE] '{title}' 문서(페이지 ID: {page_id}) Pinecone 저장 시도 중...")

    try:
        result = embed_and_store(doc)  # utils/embeddings_pinecone.py 내부 함수 호출

        if result:
            print(f"✅ [EMBED SUCCESS] '{title}' 저장 완료 → 인덱스: {result['index_name']}, 청크 수: {result['chunks']}")
            return True
        else:
            print(f"⚠️ [EMBED SKIP] '{title}' 저장할 내용이 없습니다.")
            return False

    except Exception as e:
        print(f"❌ [EMBED ERROR] '{title}' ({page_id}) 저장 실패: {e}")
        return False
