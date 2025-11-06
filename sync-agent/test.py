# test_check_pinecone.py
from utils.embeddings_pinecone import check_index_status, search_similar

print("🔍 [1] 인덱스 상태 확인 중...")
stats = check_index_status()
print(stats)

print("\n🔍 [2] 최근 문서 검색 테스트 중...")
search_similar("STT 도입에 대한 회의 내용을 알려주세요.")
