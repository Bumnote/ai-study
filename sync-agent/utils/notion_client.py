# utils/notion_client.py
"""
Notion API 클라이언트 래퍼
- 전체 페이지 메타데이터 수집
- 페이지 콘텐츠 추출
"""

import os
from typing import List, Dict, Any, Optional
from notion_client import Client
from dotenv import load_dotenv

load_dotenv()


class NotionClient:
    """Notion API 클라이언트"""
    
    def __init__(self):
        api_key = os.getenv("NOTION_API_KEY")
        if not api_key:
            raise RuntimeError("❌ NOTION_API_KEY 환경 변수가 설정되지 않았습니다.")
        self.client = Client(auth=api_key)
    
    def fetch_all_pages(self) -> List[Dict[str, Any]]:
        """워크스페이스의 모든 페이지 메타데이터 수집"""
        pages = []
        cursor = None
        
        while True:
            response = self.client.search(
                start_cursor=cursor,
                sort={"direction": "descending", "timestamp": "last_edited_time"}
            )
            
            for item in response.get("results", []):
                # 데이터베이스는 제외 (페이지만 수집)
                if item.get("object") != "page":
                    continue
                
                page_data = {
                    "id": item.get("id"),
                    "title": self._extract_title(item),
                    "url": item.get("url"),
                    "last_edited_time": item.get("last_edited_time"),
                    "created_time": item.get("created_time"),
                    "archived": item.get("archived", False),
                    "icon": self._extract_icon(item.get("icon")),
                    "cover": self._extract_cover(item.get("cover")),
                }
                
                # archived 페이지는 제외
                if not page_data["archived"]:
                    pages.append(page_data)
            
            if not response.get("has_more"):
                break
            
            cursor = response.get("next_cursor")
        
        return pages
    
    def fetch_page_content(self, page_id: str) -> str:
        """페이지의 텍스트 콘텐츠 추출"""
        blocks = self.client.blocks.children.list(block_id=page_id)
        texts = []
        
        for block in blocks.get("results", []):
            text = self._extract_text_from_block(block)
            if text:
                texts.append(text)
        
        return "\n\n".join(texts)
    
    def _extract_title(self, page: Dict[str, Any]) -> str:
        """페이지 제목 추출"""
        properties = page.get("properties", {})
        
        for prop_name, prop_value in properties.items():
            if prop_value.get("type") == "title":
                title_array = prop_value.get("title", [])
                if title_array:
                    return "".join([t.get("plain_text", "") for t in title_array])
        
        return "(제목 없음)"
    
    def _extract_text_from_block(self, block: Dict[str, Any]) -> str:
        """블록에서 텍스트 추출"""
        block_type = block.get("type")
        
        if block_type in ["paragraph", "heading_1", "heading_2", "heading_3", 
                            "bulleted_list_item", "numbered_list_item", "quote", "callout"]:
            
            block_content = block.get(block_type, {})
            rich_text = block_content.get("rich_text", [])
            
            text = "".join([t.get("plain_text", "") for t in rich_text])
            
            # 리스트 항목에는 마커 추가
            if block_type == "bulleted_list_item":
                return f"• {text}"
            elif block_type == "numbered_list_item":
                return f"- {text}"
            
            return text
        
        elif block_type == "code":
            code_content = block.get("code", {})
            rich_text = code_content.get("rich_text", [])
            code = "".join([t.get("plain_text", "") for t in rich_text])
            language = code_content.get("language", "")
            return f"```{language}\n{code}\n```"
        
        return ""
    
    def _extract_icon(self, icon: Optional[Dict[str, Any]]) -> Optional[str]:
        """아이콘 추출"""
        if not icon:
            return None
        
        if icon.get("type") == "emoji":
            return icon.get("emoji")
        elif icon.get("type") == "external":
            return icon.get("external", {}).get("url")
        elif icon.get("type") == "file":
            return icon.get("file", {}).get("url")
        
        return None
    
    def _extract_cover(self, cover: Optional[Dict[str, Any]]) -> Optional[str]:
        """커버 이미지 추출"""
        if not cover:
            return None
        
        if cover.get("type") == "external":
            return cover.get("external", {}).get("url")
        elif cover.get("type") == "file":
            return cover.get("file", {}).get("url")
        
        return None


# Backward compatibility
def get_notion_client() -> Client:
    """기존 코드 호환용 (직접 Client 반환)"""
    api_key = os.getenv("NOTION_API_KEY")
    if not api_key:
        raise RuntimeError("❌ NOTION_API_KEY 환경 변수가 설정되지 않았습니다.")
    return Client(auth=api_key)


def get_all_pages_metadata() -> List[Dict[str, Any]]:
    """기존 코드 호환용"""
    client = NotionClient()
    return client.fetch_all_pages()