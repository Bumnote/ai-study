"""
RAG 기반 챗봇 - Vector DB 검색 및 LLM 답변 생성 시스템
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_upstage import UpstageEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone


# ==================== 환경 설정 ====================
load_dotenv()

# langchain 모듈 속성 오류 우회
import langchain
if not hasattr(langchain, 'verbose'):
    langchain.verbose = False
if not hasattr(langchain, 'debug'):
    langchain.debug = False
if not hasattr(langchain, 'llm_cache'):
    langchain.llm_cache = None

MODEL_NAME = "gpt-5"
llm = ChatOpenAI(model=MODEL_NAME, temperature=0)

print("✅ 모델 초기화 완료!")


# ==================== Pinecone 벡터 DB 설정 ====================
# Pinecone 초기화
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

# 인덱스 이름 설정
OPENAI_INDEX_NAME = "notion-sync"
UPSTAGE_INDEX_NAME = "upstage-index"

# 인덱스 존재 확인
index_names = pc.list_indexes().names()
if OPENAI_INDEX_NAME in index_names:
    print(f"✅ OpenAI 인덱스 '{OPENAI_INDEX_NAME}' 존재 확인")
else:
    print(f"⚠️ OpenAI 인덱스 '{OPENAI_INDEX_NAME}'가 없습니다. Pinecone 콘솔에서 생성해주세요.")

if UPSTAGE_INDEX_NAME in index_names:
    print(f"✅ Upstage 인덱스 '{UPSTAGE_INDEX_NAME}' 존재 확인")
else:
    print(f"⚠️ Upstage 인덱스 '{UPSTAGE_INDEX_NAME}'가 없습니다. Pinecone 콘솔에서 생성해주세요.")

# 임베딩 모델 초기화
openai_embeddings = OpenAIEmbeddings(model="text-embedding-3-large")
upstage_embeddings = UpstageEmbeddings(model="solar-embedding-1-large")


# ==================== RAG 챗봇 기능 ====================

def search_similar_documents(query: str, index_name: str = "notion-sync", top_k: int = 3):
    """
    Vector DB에서 유사한 문서 검색
    
    Args:
        query: 사용자 질의
        index_name: 검색할 Pinecone 인덱스 이름 (기본값: "notion-sync")
        top_k: 가져올 상위 문서 개수
    
    Returns:
        검색된 문서 리스트 (content, metadata 포함)
    """
    print(f"\n🔍 질의 검색 중: '{query}'")
    print(f"📊 인덱스: {index_name}, 상위 {top_k}개 문서 검색")
    
    # 인덱스에 따라 적절한 임베딩 모델 선택
    if index_name == OPENAI_INDEX_NAME:
        embeddings = openai_embeddings
    elif index_name == UPSTAGE_INDEX_NAME:
        embeddings = upstage_embeddings
    else:
        raise ValueError(f"지원하지 않는 인덱스: {index_name}")
    
    # VectorStore 연결
    vectorstore = PineconeVectorStore(
        index_name=index_name,
        embedding=embeddings
    )
    
    # 유사도 검색 (score와 함께 반환)
    results = vectorstore.similarity_search_with_score(query, k=top_k)
    
    print(f"✅ {len(results)}개 문서 검색 완료\n")
    
    return results


def extract_source_info(results):
    """
    검색 결과에서 출처 정보 추출
    
    Args:
        results: similarity_search_with_score 결과
    
    Returns:
        출처 정보 리스트 (파일명, 문서타입, 생성일자, 유사도 점수)
    """
    sources = []
    seen_files = set()  # 중복 제거용
    
    for doc, score in results:
        metadata = doc.metadata
        
        # 제목과 URL 정보 추출
        title = metadata.get('title', 'Unknown')
        url = metadata.get('url', '')
        page_id = metadata.get('page_id', '')
        
        # 고유 식별자로 중복 체크
        unique_id = page_id or url or title
        if unique_id in seen_files:
            continue
        seen_files.add(unique_id)
        
        source_info = {
            'file_path': url if url else title,
            'file_name': title,
            'doc_type': metadata.get('type', metadata.get('doc_type', 'Unknown')),
            'created_at': metadata.get('created_at', metadata.get('last_edited', 'Unknown')),
            'similarity_score': round(1 - score, 4),  # 거리를 유사도로 변환
            'source': metadata.get('source', 'Unknown'),
            'page_id': page_id
        }
        sources.append(source_info)
    
    return sources


def generate_answer_with_context(query: str, contexts: list):
    """
    검색된 컨텍스트를 기반으로 LLM 답변 생성
    
    Args:
        query: 사용자 질의
        contexts: 검색된 문서 컨텍스트 리스트
    
    Returns:
        생성된 답변
    """
    # 컨텍스트 결합
    context_text = "\n\n".join([
        f"[문서 {i+1}]\n{doc.page_content}"
        for i, (doc, _) in enumerate(contexts)
    ])
    
    # RAG 프롬프트 구성
    prompt_template = """당신은 문서 기반 질의응답 전문 AI 어시스턴트입니다.

아래 제공된 문서 내용을 바탕으로 사용자의 질문에 정확하고 상세하게 답변해주세요.

[참고 문서]
{context}

[사용자 질문]
{question}

[답변 작성 가이드]
1. 제공된 문서의 내용을 기반으로만 답변하세요.
2. 문서에 없는 내용은 추측하지 말고 "문서에서 해당 정보를 찾을 수 없습니다"라고 명시하세요.
3. 구체적이고 명확하게 답변하되, 간결하게 작성하세요.
4. 답변 내용에 출처나 문서 번호를 언급하지 마세요. 순수하게 답변만 작성하세요.

답변:"""

    prompt = PromptTemplate(
        template=prompt_template,
        input_variables=["context", "question"]
    )
    
    # LLM 호출
    chain = prompt | llm
    response = chain.invoke({
        "context": context_text,
        "question": query
    })
    
    return response.content


def chat(query: str, index_name: str = "notion-sync", top_k: int = 3):
    """
    RAG 챗봇 메인 함수
    
    Args:
        query: 사용자 질의
        index_name: 검색할 인덱스 (기본값: "notion-sync")
        top_k: 검색할 문서 개수
    
    Returns:
        dict: {
            'answer': 생성된 답변,
            'sources': 출처 파일 리스트
        }
    """
    print("\n" + "="*80)
    print(f"🤖 RAG 챗봇 시작 - 인덱스: {index_name}")
    print("="*80)
    
    # Step 1: Vector DB 검색
    search_results = search_similar_documents(query, index_name, top_k)
    
    # Step 2: 출처 정보 추출
    sources = extract_source_info(search_results)
    
    # Step 3: LLM 답변 생성
    print("🧠 AI 답변 생성 중...")
    answer = generate_answer_with_context(query, search_results)
    print("✅ 답변 생성 완료\n")
    
    # 결과 반환
    result = {
        'answer': answer,
        'sources': sources,
        'index_name': index_name
    }
    
    return result


def compare_chat(query: str, top_k: int = 3):
    """
    두 인덱스(OpenAI, Upstage)에서 각각 답변을 생성하고 비교
    
    Args:
        query: 사용자 질의
        top_k: 검색할 문서 개수
    
    Returns:
        dict: {
            'openai_result': OpenAI 인덱스 답변 결과,
            'upstage_result': Upstage 인덱스 답변 결과
        }
    """
    print("\n" + "🔵"*40)
    print("📊 두 인덱스 비교 모드")
    print("🔵"*40)
    
    # OpenAI 인덱스에서 답변 생성
    print("\n" + "="*80)
    print("🔵 OpenAI 인덱스 (text-embedding-3-large)")
    print("="*80)
    openai_result = chat(query, index_name="notion-sync", top_k=top_k)
    
    # Upstage 인덱스에서 답변 생성
    print("\n" + "="*80)
    print("🟣 Upstage 인덱스 (solar-embedding-1-large)")
    print("="*80)
    upstage_result = chat(query, index_name="upstage-index", top_k=top_k)

    return {
        'openai_result': openai_result,
        'upstage_result': upstage_result
    }


def print_chat_result(result: dict):
    """챗봇 결과를 보기 좋게 출력"""
    print("\n" + "="*80)
    print("💬 답변")
    print("="*80)
    print(result['answer'])
    print("\n" + "-"*80)
    print("📚 참고 문서 출처")
    print("-"*80)
    
    for i, source in enumerate(result['sources'], 1):
        print(f"\n[{i}] {source['file_name']}")
        print(f"    • 출처: {source['source']}")
        print(f"    • 문서 타입: {source['doc_type']}")
        print(f"    • 생성 일자: {source['created_at']}")
        print(f"    • 유사도: {source['similarity_score']}")
        if source.get('file_path') and source['file_path'].startswith('http'):
            print(f"    • URL: {source['file_path']}")
    
    print("\n" + "="*80)


def print_comparison_result(openai_result: dict, upstage_result: dict):
    """두 인덱스의 답변을 비교하여 출력"""
    print("\n" + "🔵"*40)
    print("📊 답변 비교 결과")
    print("🔵"*40)
    
    # OpenAI 결과
    print("\n" + "🔵"*40)
    print("🔵 OpenAI 인덱스 답변 (text-embedding-3-large)")
    print("🔵"*40)
    print_chat_result(openai_result)
    
    # Upstage 결과
    print("\n" + "🟣"*40)
    print("🟣 Upstage 인덱스 답변 (solar-embedding-1-large)")
    print("🟣"*40)
    print_chat_result(upstage_result)
    
    # 비교 요약
    print("\n" + "📊"*40)
    print("📊 비교 요약")
    print("📊"*40)
    print(f"\n🔵 OpenAI 답변 길이: {len(openai_result['answer'])} 자")
    print(f"🔵 OpenAI 참고 문서: {len(openai_result['sources'])}개")
    if openai_result['sources']:
        print(f"🔵 OpenAI 평균 유사도: {sum(s['similarity_score'] for s in openai_result['sources']) / len(openai_result['sources']):.4f}")
    
    print(f"\n🟣 Upstage 답변 길이: {len(upstage_result['answer'])} 자")
    print(f"🟣 Upstage 참고 문서: {len(upstage_result['sources'])}개")
    if upstage_result['sources']:
        print(f"🟣 Upstage 평균 유사도: {sum(s['similarity_score'] for s in upstage_result['sources']) / len(upstage_result['sources']):.4f}")
    
    print("\n" + "="*80)


# ==================== 실행 ====================

if __name__ == "__main__":
    import sys
    
    print("\n[RAG 챗봇 모드]")
    print("="*80)
    
    # 명령행 인자 파싱
    if len(sys.argv) > 1:
        # 비교 모드 확인
        if sys.argv[1] == "compare":
            # 비교 모드
            if len(sys.argv) > 2:
                query = " ".join(sys.argv[2:])
                comparison = compare_chat(query, top_k=3)
                print_comparison_result(comparison['openai_result'], comparison['upstage_result'])
            else:
                # 테스트 질의로 비교
                print("\n테스트 질의로 두 인덱스를 비교합니다...\n")
                test_query = "회의에서 논의된 주요 내용은 무엇인가요?"
                print(f"질의: {test_query}\n")
                comparison = compare_chat(test_query, top_k=3)
                print_comparison_result(comparison['openai_result'], comparison['upstage_result'])
        else:
            # 단일 질의 모드 (기본 notion-sync)
            query = " ".join(sys.argv[1:])
            result = chat(query, index_name="notion-sync", top_k=3)
            print_chat_result(result)
    else:
        # 테스트 모드 - 비교 모드로 여러 질의 실행
        print("\n테스트 질의를 두 인덱스에서 비교합니다...\n")
        
        test_queries = [
            "회의에서 논의된 주요 내용은 무엇인가요?",
            "성능 개선과 관련되어 어떤 논의가 있었나요?",
            "기술적으로 개선이 필요한 부분은 무엇인가요?"
        ]
        
        for idx, query in enumerate(test_queries, 1):
            print(f"\n\n{'🔷'*40}")
            print(f"테스트 질의 {idx}/{len(test_queries)}: {query}")
            print('🔷'*40)
            
            comparison = compare_chat(query, top_k=3)
            print_comparison_result(comparison['openai_result'], comparison['upstage_result'])
            
            if idx < len(test_queries):
                print("\n" + "─"*80 + "\n")
    
    print("\n사용법:")
    print("  python rag_chat.py                              # 테스트 모드 (비교)")
    print("  python rag_chat.py compare                      # 비교 모드 (테스트 질의)")
    print("  python rag_chat.py compare 질문을 입력하세요     # 비교 모드 (커스텀 질의)")
    print("  python rag_chat.py 질문을 입력하세요             # 단일 모드 (OpenAI 인덱스)")
