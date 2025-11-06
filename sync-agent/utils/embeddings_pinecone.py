# utils/embeddings_pinecone.py
"""
OpenAI Embeddings + Pinecone 직접 연동 모듈 (안정화 버전)
- text-embedding-3-large (3072차원)
- batch 업서트
- 자동 리트라이 및 예외 처리 강화
"""

import os
import time
from datetime import datetime
from typing import Dict, List
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

# ======================================
# ⚙️ Pinecone 설정
# ======================================
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENVIRONMENT")
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

if not PINECONE_API_KEY:
    raise ValueError("❌ PINECONE_API_KEY 환경 변수가 설정되지 않았습니다.")

# Pinecone 클라이언트 초기화
pc = Pinecone(api_key=PINECONE_API_KEY)

# 인덱스 확인 및 생성
indexes = [idx["name"] for idx in pc.list_indexes()]
if INDEX_NAME not in indexes:
    print(f"🆕 Pinecone 인덱스 '{INDEX_NAME}' 생성 중...")
    pc.create_index(
        name=INDEX_NAME,
        dimension=3072,  # text-embedding-3-large
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region=PINECONE_ENV),
    )
    print(f"✅ 인덱스 생성 완료")
else:
    print(f"✅ Pinecone 인덱스 '{INDEX_NAME}' 연결 완료")

# 인덱스 핸들
index = pc.Index(INDEX_NAME)

# OpenAI Embeddings 초기화
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

# ======================================
# 🧩 텍스트 분할 유틸
# ======================================
def split_text(text: str, doc_type: str = None) -> List[str]:
    """문서를 의미 단위로 분리"""
    if not text.strip():
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=["\n\n", "\n", ".", " "],
    )
    chunks = splitter.split_text(text)
    print(f"🪓 '{doc_type or '문서'}' → {len(chunks)}개 청크로 분리 완료")
    return chunks


# ======================================
# 🧠 Embedding & Pinecone 저장 함수
# ======================================
def embed_and_store(doc: Dict):
    """
    문서를 Pinecone에 임베딩하여 저장합니다.
    입력 예시:
        {
            "title": "회의록",
            "doc_type": "기술 회의",
            "summary": "문서 내용...",
            "source": "notion",
            "last_edited_time": "2025-11-05T09:00:00Z",
            "url": "https://notion.so/abcd1234",
            "page_id": "abcd1234"
        }
    """
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

    title = doc.get("title", "Untitled")
    doc_type = doc.get("doc_type", "미분류")
    text = doc.get("summary", "")
    url = doc.get("url", "")
    source = doc.get("source", "unknown")
    page_id = doc.get("page_id", "unknown")

    if not text.strip():
        print(f"⚠️ [SKIP] '{title}' 문서에 내용이 없습니다.")
        return None

    # 1️⃣ 텍스트 분할
    chunks = split_text(text, doc_type)
    vectors_to_upsert = []

    # 2️⃣ 각 청크별 Embedding 생성
    for i, chunk in enumerate(chunks):
        try:
            vector = embeddings.embed_query(chunk)
            if not vector or len(vector) != 3072:  # text-embedding-3-large는 3072차원
                print(f"⚠️ [EMBED WARN] 임베딩 실패 (chunk {i+1}, dim={len(vector) if vector else 0}) → 건너뜀")
                continue

            vector_id = f"{page_id}_{i}".replace(" ", "_")
            metadata = {
                "page_id": page_id,
                "title": title,
                "type": doc_type,
                "url": url,
                "source": source,
                "text": chunk, 
                "chunk_index": i,
                "chunk_total": len(chunks),
                "last_edited": doc.get("last_edited_time", ""),
                "created_at": datetime.utcnow().isoformat(),
            }

            vectors_to_upsert.append({
                "id": vector_id,
                "values": vector,
                "metadata": metadata,
            })
        except Exception as e:
            print(f"❌ [EMBED ERROR] chunk {i+1} 실패: {e}")

    # 3️⃣ Pinecone 업서트 (Batch)
    if vectors_to_upsert:
        try:
            print(f"📦 Pinecone에 {len(vectors_to_upsert)}개 벡터 업서트 중...")
            index.upsert(vectors=vectors_to_upsert)
            time.sleep(0.5)  # flush 대기
            print(f"✅ '{title}' 문서 저장 완료 ({len(vectors_to_upsert)}개 청크)")
        except Exception as e:
            print(f"❌ [UPSERT ERROR] Pinecone 저장 실패: {e}")
    else:
        print(f"⚠️ [SKIP] '{title}' 저장할 벡터 없음")

    return {
        "title": title,
        "index_name": INDEX_NAME,
        "chunks": len(vectors_to_upsert),
    }


# ======================================
# 🔍 검색 (테스트용)
# ======================================
def search_similar(query: str, top_k: int = 5):
    """쿼리 문장과 유사한 벡터를 Pinecone에서 검색"""
    embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
    query_vector = embeddings.embed_query(query)

    try:
        res = index.query(
            vector=query_vector,
            top_k=top_k,
            include_metadata=True,
        )

        print(f"\n🔎 '{query}'와 유사한 문서 {len(res['matches'])}개 발견:")
        for match in res["matches"]:
            meta = match["metadata"]
            print(f"  📄 {meta.get('title')} ({meta.get('type')}) → score={match['score']:.3f}")
        return res

    except Exception as e:
        print(f"❌ [QUERY ERROR] 검색 실패: {e}")
        return None


# ======================================
# 🧾 인덱스 상태 점검 함수
# ======================================
def check_index_status():
    """현재 인덱스의 벡터 개수 및 상태 확인"""
    stats = index.describe_index_stats()
    count = stats.get("total_vector_count", 0)
    print(f"📊 현재 저장된 벡터 수: {count}")
    return stats
