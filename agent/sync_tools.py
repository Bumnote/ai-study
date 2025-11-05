"""
동기화 관련 도구들
Notion 페이지 메타데이터 수집 및 임베딩 동기화
"""
import os
import json
import aiohttp
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from langchain_core.tools import tool
from dotenv import load_dotenv

load_dotenv()

# Notion API 설정
NOTION_TOKEN = os.getenv("NOTION_API_KEY")
NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"

# 동기화 상태 파일
SYNC_STATE_FILE = "sync_state.json"
EMBEDDINGS_DB_FILE = "embeddings_metadata.json"


# ============================================================
# 동기화 상태 관리
# ============================================================
class SyncStateManager:
    """동기화 상태 관리"""
    
    @staticmethod
    def load() -> Dict:
        """저장된 동기화 상태 불러오기"""
        if Path(SYNC_STATE_FILE).exists():
            with open(SYNC_STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"last_sync_time": None, "total_synced": 0}
    
    @staticmethod
    def save(sync_time: str, synced_count: int):
        """동기화 상태 저장"""
        state = SyncStateManager.load()
        state["last_sync_time"] = sync_time
        state["total_synced"] = state.get("total_synced", 0) + synced_count
        
        with open(SYNC_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)


class EmbeddingDBManager:
    """임베딩 메타데이터 관리"""
    
    @staticmethod
    def load() -> Dict:
        """저장된 임베딩 메타데이터 불러오기"""
        if Path(EMBEDDINGS_DB_FILE).exists():
            with open(EMBEDDINGS_DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    @staticmethod
    def save(embeddings: Dict):
        """임베딩 메타데이터 저장"""
        with open(EMBEDDINGS_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(embeddings, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def should_embed(page_id: str, last_edited_time: str) -> bool:
        """해당 페이지를 임베딩해야 하는지 확인"""
        embeddings = EmbeddingDBManager.load()
        
        if page_id not in embeddings:
            return True  # 새 페이지
        
        existing_time = embeddings[page_id].get('last_edited_time', '')
        return last_edited_time > existing_time  # 수정된 페이지


# ============================================================
# Notion API 호출 함수들
# ============================================================
async def _fetch_notion_pages(after_date: Optional[str] = None) -> List[Dict]:
    """Notion API를 통해 페이지 가져오기"""
    if not NOTION_TOKEN:
        return []
    
    url = f"{BASE_URL}/search"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json"
    }
    
    all_results = []
    has_more = True
    start_cursor = None
    
    async with aiohttp.ClientSession() as session:
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
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get("results", [])
                        
                        # 날짜 필터링
                        if after_date:
                            filtered_results = [
                                page for page in results
                                if _is_after_date(page, after_date)
                            ]
                            all_results.extend(filtered_results)
                            
                            # 모든 결과가 after_date 이전이면 중단
                            if not filtered_results and results:
                                break
                        else:
                            all_results.extend(results)
                        
                        has_more = data.get("has_more", False)
                        start_cursor = data.get("next_cursor")
                    else:
                        break
            except Exception as e:
                print(f"❌ API 호출 오류: {e}")
                break
    
    return all_results


def _is_after_date(page: Dict, after_date: str) -> bool:
    """페이지가 특정 날짜 이후에 생성/수정되었는지 확인"""
    created_time = page.get('created_time', '')
    edited_time = page.get('last_edited_time', '')
    return created_time > after_date or edited_time > after_date


def _extract_title(page: Dict) -> str:
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


async def _get_page_content_for_embedding(page_id: str) -> Optional[str]:
    """페이지 컨텐츠 가져오기 (임베딩용)"""
    if not NOTION_TOKEN:
        return None
    
    url = f"{BASE_URL}/blocks/{page_id}/children"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    blocks = data.get("results", [])
                    
                    content_parts = []
                    for block in blocks:
                        text = _extract_text_from_block(block)
                        if text:
                            content_parts.append(text)
                    
                    return "\n\n".join(content_parts)
        except Exception as e:
            print(f"⚠️ 페이지 {page_id} 컨텐츠 가져오기 실패: {e}")
    
    return None


def _extract_text_from_block(block: Dict) -> str:
    """블록에서 텍스트 추출"""
    block_type = block.get("type", "")
    block_content = block.get(block_type, {})
    
    if "rich_text" in block_content:
        texts = [rt.get("plain_text", "") for rt in block_content["rich_text"]]
        return "".join(texts)
    
    return ""


# ============================================================
# LangChain Tools
# ============================================================
@tool
async def check_sync_status() -> dict:
    """
    현재 동기화 상태를 확인합니다.
    마지막 동기화 시간, 총 동기화된 페이지 수, 현재 임베딩 수를 반환합니다.
    """
    print("--- 동기화 상태 확인 ---")
    
    sync_state = SyncStateManager.load()
    embeddings = EmbeddingDBManager.load()
    
    result = {
        "last_sync_time": sync_state.get("last_sync_time"),
        "total_synced": sync_state.get("total_synced", 0),
        "current_embeddings": len(embeddings),
        "status": "initialized" if sync_state.get("last_sync_time") else "not_synced"
    }
    
    if sync_state.get("last_sync_time"):
        last_sync = datetime.fromisoformat(sync_state["last_sync_time"].replace('Z', '+00:00'))
        time_since = datetime.now(timezone.utc) - last_sync
        result["hours_since_sync"] = time_since.total_seconds() / 3600
    
    return result


@tool
async def full_sync_notion() -> dict:
    """
    Notion 워크스페이스의 모든 페이지를 전체 동기화합니다.
    모든 페이지를 가져와서 임베딩을 생성하고 메타데이터를 저장합니다.
    첫 실행 시 또는 전체 재동기화가 필요할 때 사용합니다.
    """
    print("--- 전체 동기화 시작 ---")
    
    if not NOTION_TOKEN:
        return {"error": "NOTION_API_KEY가 설정되지 않았습니다.", "success": False}
    
    try:
        # 모든 페이지 가져오기
        pages = await _fetch_notion_pages(after_date=None)
        
        if not pages:
            return {
                "success": True,
                "message": "페이지를 찾을 수 없습니다.",
                "new_count": 0,
                "updated_count": 0
            }
        
        embeddings = EmbeddingDBManager.load()
        new_count = 0
        updated_count = 0
        
        # 각 페이지 처리
        for page in pages:
            page_id = page.get('id')
            title = _extract_title(page)
            last_edited_time = page.get('last_edited_time', '')
            
            is_new = page_id not in embeddings
            
            # 컨텐츠 가져오기
            content = await _get_page_content_for_embedding(page_id)
            
            if content:
                # 메타데이터 저장 (TODO: 실제 임베딩 생성 추가)
                embeddings[page_id] = {
                    'title': title,
                    'created_time': page.get('created_time', ''),
                    'last_edited_time': last_edited_time,
                    'url': page.get('url', ''),
                    'content_length': len(content),
                    'embedded_at': datetime.now(timezone.utc).isoformat(),
                    'object': page.get('object', 'page')
                }
                
                if is_new:
                    new_count += 1
                else:
                    updated_count += 1
        
        # 상태 저장
        current_time = datetime.now(timezone.utc).isoformat()
        EmbeddingDBManager.save(embeddings)
        SyncStateManager.save(current_time, new_count + updated_count)
        
        return {
            "success": True,
            "message": "전체 동기화 완료",
            "total_pages": len(pages),
            "new_count": new_count,
            "updated_count": updated_count,
            "total_embeddings": len(embeddings)
        }
    
    except Exception as e:
        return {"error": str(e), "success": False}


@tool
async def incremental_sync_notion() -> dict:
    """
    마지막 동기화 이후 변경된 Notion 페이지만 증분 동기화합니다.
    새로 생성되거나 수정된 페이지만 처리하여 빠르고 효율적입니다.
    일상적인 동기화에 사용합니다.
    """
    print("--- 증분 동기화 시작 ---")
    
    if not NOTION_TOKEN:
        return {"error": "NOTION_API_KEY가 설정되지 않았습니다.", "success": False}
    
    sync_state = SyncStateManager.load()
    last_sync_time = sync_state.get("last_sync_time")
    
    if not last_sync_time:
        return {
            "error": "마지막 동기화 기록이 없습니다. 먼저 전체 동기화를 실행하세요.",
            "success": False,
            "suggestion": "full_sync_notion 도구를 사용하세요."
        }
    
    try:
        # 마지막 동기화 이후 변경된 페이지만 가져오기
        pages = await _fetch_notion_pages(after_date=last_sync_time)
        
        if not pages:
            return {
                "success": True,
                "message": "변경된 페이지가 없습니다.",
                "new_count": 0,
                "updated_count": 0
            }
        
        embeddings = EmbeddingDBManager.load()
        new_count = 0
        updated_count = 0
        skipped_count = 0
        
        # 각 페이지 처리
        for page in pages:
            page_id = page.get('id')
            title = _extract_title(page)
            last_edited_time = page.get('last_edited_time', '')
            
            # 임베딩이 필요한지 확인
            if not EmbeddingDBManager.should_embed(page_id, last_edited_time):
                skipped_count += 1
                continue
            
            is_new = page_id not in embeddings
            
            # 컨텐츠 가져오기
            content = await _get_page_content_for_embedding(page_id)
            
            if content:
                # 메타데이터 저장 (TODO: 실제 임베딩 생성 추가)
                embeddings[page_id] = {
                    'title': title,
                    'created_time': page.get('created_time', ''),
                    'last_edited_time': last_edited_time,
                    'url': page.get('url', ''),
                    'content_length': len(content),
                    'embedded_at': datetime.now(timezone.utc).isoformat(),
                    'object': page.get('object', 'page')
                }
                
                if is_new:
                    new_count += 1
                else:
                    updated_count += 1
        
        # 상태 저장
        current_time = datetime.now(timezone.utc).isoformat()
        EmbeddingDBManager.save(embeddings)
        SyncStateManager.save(current_time, new_count + updated_count)
        
        return {
            "success": True,
            "message": "증분 동기화 완료",
            "changes_found": len(pages),
            "new_count": new_count,
            "updated_count": updated_count,
            "skipped_count": skipped_count,
            "total_embeddings": len(embeddings)
        }
    
    except Exception as e:
        return {"error": str(e), "success": False}


@tool
async def auto_sync_after_notion_action() -> dict:
    """
    Notion에서 문서 생성/수정 후 자동으로 호출되는 동기화 함수입니다.
    증분 동기화를 실행하여 최신 변경사항을 반영합니다.
    """
    print("--- 자동 동기화 트리거 ---")
    
    # 증분 동기화 실행
    result = await incremental_sync_notion()
    
    if result.get("success"):
        result["triggered_by"] = "auto_sync"
        result["message"] = "자동 동기화 완료 - 최신 Notion 변경사항이 반영되었습니다."
    
    return result