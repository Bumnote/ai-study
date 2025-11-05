import asyncio
import json
import aiohttp
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional

# Notion API 설정
NOTION_TOKEN = "your_notion_api_key_here"  # 실제 API 키로 변경
NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"

# 동기화 상태 파일
SYNC_STATE_FILE = "sync_state.json"
EMBEDDINGS_DB_FILE = "embeddings_metadata.json"


class SyncState:
    """동기화 상태 관리 클래스"""
    
    def __init__(self, filepath: str = SYNC_STATE_FILE):
        self.filepath = filepath
        self.last_sync_time = None
        self.total_synced = 0
        self.load()
    
    def load(self):
        """저장된 동기화 상태 불러오기"""
        if Path(self.filepath).exists():
            with open(self.filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.last_sync_time = data.get('last_sync_time')
                self.total_synced = data.get('total_synced', 0)
                print(f"📂 마지막 동기화: {self.last_sync_time}")
        else:
            print("📂 첫 동기화입니다.")
    
    def save(self, sync_time: str, synced_count: int):
        """동기화 상태 저장"""
        self.last_sync_time = sync_time
        self.total_synced += synced_count
        
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump({
                'last_sync_time': self.last_sync_time,
                'total_synced': self.total_synced
            }, f, ensure_ascii=False, indent=2)
        
        print(f"💾 동기화 상태 저장: {sync_time}")


class NotionSyncManager:
    """Notion 증분 동기화 매니저"""
    
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json"
        }
    
    async def get_pages_after_date(
        self, 
        session: aiohttp.ClientSession, 
        after_date: Optional[str] = None
    ) -> List[Dict]:
        """특정 날짜 이후 생성/수정된 페이지 가져오기"""
        url = f"{BASE_URL}/search"
        
        all_results = []
        has_more = True
        start_cursor = None
        
        print(f"\n🔍 {'전체' if not after_date else after_date + ' 이후'} 페이지 검색 중...")
        
        while has_more:
            payload = {
                "sort": {
                    "direction": "descending",
                    "timestamp": "last_edited_time"
                }
            }
            
            if start_cursor:
                payload["start_cursor"] = start_cursor
            
            try:
                async with session.post(url, json=payload, headers=self.headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get("results", [])
                        
                        # 날짜 필터링
                        if after_date:
                            filtered_results = [
                                page for page in results
                                if self._is_after_date(page, after_date)
                            ]
                            all_results.extend(filtered_results)
                            
                            # 모든 결과가 after_date 이전이면 중단
                            if not filtered_results and results:
                                print(f"  ✅ 모든 최신 페이지 수집 완료")
                                break
                        else:
                            all_results.extend(results)
                        
                        has_more = data.get("has_more", False)
                        start_cursor = data.get("next_cursor")
                        
                        print(f"  📄 {len(all_results)}개 페이지 발견...")
                    else:
                        error_text = await response.text()
                        print(f"❌ API 오류: {error_text}")
                        break
            except Exception as e:
                print(f"❌ 요청 오류: {e}")
                break
        
        return all_results
    
    def _is_after_date(self, page: Dict, after_date: str) -> bool:
        """페이지가 특정 날짜 이후에 생성/수정되었는지 확인"""
        created_time = page.get('created_time', '')
        edited_time = page.get('last_edited_time', '')
        
        return created_time > after_date or edited_time > after_date
    
    async def get_page_content(
        self, 
        session: aiohttp.ClientSession, 
        page_id: str
    ) -> Optional[str]:
        """페이지의 실제 컨텐츠 가져오기 (블록 단위)"""
        url = f"{BASE_URL}/blocks/{page_id}/children"
        
        try:
            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    blocks = data.get("results", [])
                    
                    # 블록에서 텍스트 추출
                    content_parts = []
                    for block in blocks:
                        text = self._extract_text_from_block(block)
                        if text:
                            content_parts.append(text)
                    
                    return "\n\n".join(content_parts)
                else:
                    return None
        except Exception as e:
            print(f"  ⚠️ 페이지 {page_id} 컨텐츠 가져오기 실패: {e}")
            return None
    
    def _extract_text_from_block(self, block: Dict) -> str:
        """블록에서 텍스트 추출"""
        block_type = block.get("type", "")
        block_content = block.get(block_type, {})
        
        # rich_text 필드에서 텍스트 추출
        if "rich_text" in block_content:
            texts = [
                rt.get("plain_text", "") 
                for rt in block_content["rich_text"]
            ]
            return "".join(texts)
        
        return ""


class EmbeddingManager:
    """임베딩 메타데이터 관리 클래스"""
    
    def __init__(self, filepath: str = EMBEDDINGS_DB_FILE):
        self.filepath = filepath
        self.embeddings_metadata = {}
        self.load()
    
    def load(self):
        """저장된 임베딩 메타데이터 불러오기"""
        if Path(self.filepath).exists():
            with open(self.filepath, 'r', encoding='utf-8') as f:
                self.embeddings_metadata = json.load(f)
                print(f"📊 기존 임베딩: {len(self.embeddings_metadata)}개")
        else:
            print("📊 임베딩 데이터베이스 초기화")
    
    def save(self):
        """임베딩 메타데이터 저장"""
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(self.embeddings_metadata, f, ensure_ascii=False, indent=2)
    
    def add_or_update(self, page_id: str, metadata: Dict):
        """임베딩 메타데이터 추가 또는 업데이트"""
        self.embeddings_metadata[page_id] = metadata
    
    def should_embed(self, page_id: str, last_edited_time: str) -> bool:
        """해당 페이지를 임베딩해야 하는지 확인"""
        if page_id not in self.embeddings_metadata:
            return True  # 새 페이지
        
        existing_edited_time = self.embeddings_metadata[page_id].get('last_edited_time', '')
        return last_edited_time > existing_edited_time  # 수정된 페이지
    
    def get_stats(self) -> Dict:
        """통계 정보 반환"""
        return {
            'total_embeddings': len(self.embeddings_metadata),
            'pages': list(self.embeddings_metadata.keys())
        }


async def create_embeddings_for_pages(
    pages: List[Dict], 
    sync_manager: NotionSyncManager,
    embedding_manager: EmbeddingManager,
    session: aiohttp.ClientSession
):
    """페이지들을 임베딩 처리 (실제 임베딩은 여기서 구현)"""
    
    new_embeddings = 0
    updated_embeddings = 0
    
    for i, page in enumerate(pages, 1):
        page_id = page.get('id')
        title = extract_title(page)
        last_edited_time = page.get('last_edited_time', '')
        
        # 임베딩이 필요한지 확인
        if not embedding_manager.should_embed(page_id, last_edited_time):
            print(f"  ⏭️  [{i}/{len(pages)}] {title[:30]} - 이미 최신 상태")
            continue
        
        is_new = page_id not in embedding_manager.embeddings_metadata
        
        print(f"  {'🆕' if is_new else '🔄'} [{i}/{len(pages)}] {title[:40]} 처리 중...")
        
        # 페이지 컨텐츠 가져오기
        content = await sync_manager.get_page_content(session, page_id)
        
        if content:
            # TODO: 여기서 실제 임베딩 생성 (OpenAI, Cohere 등)
            # embedding_vector = await create_embedding(content)
            
            # 메타데이터 저장
            embedding_manager.add_or_update(page_id, {
                'title': title,
                'created_time': page.get('created_time', ''),
                'last_edited_time': last_edited_time,
                'url': page.get('url', ''),
                'content_length': len(content),
                'embedded_at': datetime.now(timezone.utc).isoformat(),
                # 'embedding_vector': embedding_vector  # 실제 벡터 저장
            })
            
            if is_new:
                new_embeddings += 1
            else:
                updated_embeddings += 1
        else:
            print(f"    ⚠️ 컨텐츠를 가져올 수 없습니다.")
    
    return new_embeddings, updated_embeddings


def extract_title(page: Dict) -> str:
    """페이지 제목 추출"""
    object_type = page.get('object')
    
    if object_type == 'database':
        title_array = page.get('title', [])
        if title_array:
            return title_array[0].get('plain_text', 'Untitled')
    
    elif object_type == 'page':
        properties = page.get('properties', {})
        for key, value in properties.items():
            if isinstance(value, dict) and value.get('type') == 'title':
                title_array = value.get('title', [])
                if title_array:
                    return title_array[0].get('plain_text', 'Untitled')
    
    return 'Untitled'


async def full_sync():
    """전체 동기화 (첫 실행 시)"""
    print("="*70)
    print("🔄 전체 동기화 시작")
    print("="*70)
    
    sync_state = SyncState()
    embedding_manager = EmbeddingManager()
    sync_manager = NotionSyncManager(NOTION_TOKEN)
    
    async with aiohttp.ClientSession() as session:
        # 모든 페이지 가져오기
        pages = await sync_manager.get_pages_after_date(session, None)
        
        print(f"\n📊 총 {len(pages)}개 페이지 발견")
        
        if pages:
            # 임베딩 생성
            new_count, updated_count = await create_embeddings_for_pages(
                pages, sync_manager, embedding_manager, session
            )
            
            # 상태 저장
            current_time = datetime.now(timezone.utc).isoformat()
            embedding_manager.save()
            sync_state.save(current_time, new_count + updated_count)
            
            print(f"\n✅ 동기화 완료!")
            print(f"  🆕 새 임베딩: {new_count}개")
            print(f"  🔄 업데이트: {updated_count}개")
            print(f"  📊 총 임베딩: {len(embedding_manager.embeddings_metadata)}개")


async def incremental_sync():
    """증분 동기화 (마지막 동기화 이후 변경된 것만)"""
    print("="*70)
    print("⚡ 증분 동기화 시작")
    print("="*70)
    
    sync_state = SyncState()
    
    if not sync_state.last_sync_time:
        print("\n⚠️ 마지막 동기화 기록이 없습니다.")
        print("전체 동기화를 먼저 실행하세요.")
        return
    
    embedding_manager = EmbeddingManager()
    sync_manager = NotionSyncManager(NOTION_TOKEN)
    
    async with aiohttp.ClientSession() as session:
        # 마지막 동기화 이후 변경된 페이지만 가져오기
        pages = await sync_manager.get_pages_after_date(
            session, 
            sync_state.last_sync_time
        )
        
        print(f"\n📊 {sync_state.last_sync_time} 이후 {len(pages)}개 페이지 변경됨")
        
        if pages:
            # 임베딩 생성/업데이트
            new_count, updated_count = await create_embeddings_for_pages(
                pages, sync_manager, embedding_manager, session
            )
            
            # 상태 저장
            current_time = datetime.now(timezone.utc).isoformat()
            embedding_manager.save()
            sync_state.save(current_time, new_count + updated_count)
            
            print(f"\n✅ 증분 동기화 완료!")
            print(f"  🆕 새 임베딩: {new_count}개")
            print(f"  🔄 업데이트: {updated_count}개")
            print(f"  📊 총 임베딩: {len(embedding_manager.embeddings_metadata)}개")
        else:
            print("\n✅ 변경된 페이지가 없습니다.")


async def show_status():
    """현재 동기화 상태 확인"""
    print("="*70)
    print("📊 동기화 상태")
    print("="*70)
    
    sync_state = SyncState()
    embedding_manager = EmbeddingManager()
    
    stats = embedding_manager.get_stats()
    
    print(f"\n마지막 동기화: {sync_state.last_sync_time or '없음'}")
    print(f"총 동기화된 페이지: {sync_state.total_synced}개")
    print(f"현재 임베딩 수: {stats['total_embeddings']}개")
    
    if sync_state.last_sync_time:
        last_sync = datetime.fromisoformat(sync_state.last_sync_time.replace('Z', '+00:00'))
        time_since = datetime.now(timezone.utc) - last_sync
        print(f"경과 시간: {time_since.days}일 {time_since.seconds//3600}시간")


def print_menu():
    """메뉴 출력"""
    print("\n" + "="*70)
    print("🚀 Notion 증분 동기화 시스템")
    print("="*70)
    print("\n옵션을 선택하세요:")
    print("  1. 전체 동기화 (첫 실행 또는 전체 재동기화)")
    print("  2. 증분 동기화 (마지막 동기화 이후 변경사항만)")
    print("  3. 상태 확인")
    print("  4. 종료")
    print()


async def main():
    """메인 함수"""
    
    if NOTION_TOKEN == "your_notion_api_key_here":
        print("❌ NOTION_TOKEN을 설정해주세요.")
        return
    
    while True:
        print_menu()
        choice = input("선택 (1-4): ").strip()
        
        if choice == "1":
            await full_sync()
        elif choice == "2":
            await incremental_sync()
        elif choice == "3":
            await show_status()
        elif choice == "4":
            print("\n👋 프로그램을 종료합니다.")
            break
        else:
            print("❌ 잘못된 입력입니다.")


if __name__ == "__main__":
    try:
        import aiohttp
    except ImportError:
        print("❌ aiohttp가 필요합니다: pip install aiohttp")
        exit(1)
    
    asyncio.run(main())