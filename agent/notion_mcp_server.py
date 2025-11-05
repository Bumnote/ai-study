import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from fastmcp import FastMCP
from notion_client import Client

load_dotenv()
mcp = FastMCP("Notion MCP Server")

def _get_notion_client() -> Client:
    api_key = os.getenv("NOTION_API_KEY")
    if not api_key:
        raise RuntimeError("NOTION_API_KEY가 설정되지 않았습니다.")
    return Client(auth=api_key)

def _page_title_from(obj: Dict[str, Any]) -> str:
    # 페이지/DB title 추출 시도 (best-effort)
    props = obj.get("properties", {}) or {}
    for v in props.values():
        if v and v.get("type") == "title":
            rich = v.get("title") or []
            return "".join([t.get("plain_text", "") for t in rich]) or "(제목 없음)"
    # 데이터베이스는 title 속성이 다름
    if obj.get("object") == "database":
        title = obj.get("title") or []
        return "".join([t.get("plain_text", "") for t in title]) or "(데이터베이스)"
    return "(제목 없음)"

def _collect_block_texts(client: Client, block_id: str, limit: int = 2000) -> str:
    texts: List[str] = []
    cursor: Optional[str] = None
    fetched = 0
    while True:
        resp = client.blocks.children.list(block_id=block_id, start_cursor=cursor)
        for b in resp.get("results", []):
            t = []
            # common rich_text
            rich = None
            if "paragraph" in b:
                rich = b["paragraph"].get("rich_text", [])
            elif "heading_1" in b:
                rich = b["heading_1"].get("rich_text", [])
            elif "heading_2" in b:
                rich = b["heading_2"].get("rich_text", [])
            elif "heading_3" in b:
                rich = b["heading_3"].get("rich_text", [])
            elif "bulleted_list_item" in b:
                rich = b["bulleted_list_item"].get("rich_text", [])
            elif "numbered_list_item" in b:
                rich = b["numbered_list_item"].get("rich_text", [])
            elif "to_do" in b:
                rich = b["to_do"].get("rich_text", [])
            if rich:
                t.append("".join([r.get("plain_text", "") for r in rich]))
            if t:
                texts.append("\n".join(t))
                fetched += 1
                if fetched >= limit:
                    break
        if fetched >= limit:
            break
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")
    return "\n".join(texts)

# ✅ 코어 함수 정의 (데코레이터 없이)
def _search_notion_impl(query: str) -> dict:
    """Notion에서 키워드로 페이지/데이터베이스 검색 (구현부)"""
    try:
        client = _get_notion_client()
        result = client.search(query=query)
        items = []
        for r in result.get("results", []):
            items.append({
                "id": r.get("id"),
                "object": r.get("object"),
                "title": _page_title_from(r),
            })
        return {"count": len(items), "results": items}
    except Exception as e:
        return {"error": str(e)}

def _get_page_content_impl(page_id: str) -> dict:
    """Notion 페이지의 텍스트 콘텐츠를 추출 (구현부)"""
    try:
        client = _get_notion_client()
        page = client.pages.retrieve(page_id=page_id)
        title = _page_title_from(page)
        text = _collect_block_texts(client, page_id)
        return {"page_id": page_id, "title": title, "text": text}
    except Exception as e:
        return {"error": str(e), "page_id": page_id}

def _update_page_impl(page_id: str, summary: str) -> dict:
    """Notion 페이지에 요약 결과를 업데이트 (구현부)"""
    try:
        client = _get_notion_client()
        client.blocks.children.append(
            block_id=page_id,
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {"type": "text", "text": {"content": summary}}
                        ]
                    },
                }
            ],
        )
        return {"status": "updated", "page_id": page_id}
    except Exception as e:
        return {"error": str(e), "page_id": page_id}

# ✅ FastMCP 도구로 등록 (MCP 서버용)
@mcp.tool
def search_notion(query: str) -> dict:
    """Notion에서 키워드로 페이지/데이터베이스 검색"""
    return _search_notion_impl(query)

@mcp.tool
def get_page_content(page_id: str) -> dict:
    """Notion 페이지의 텍스트 콘텐츠를 추출"""
    return _get_page_content_impl(page_id)

@mcp.tool
def update_page(page_id: str, summary: str) -> dict:
    """Notion 페이지에 요약 결과를 업데이트"""
    return _update_page_impl(page_id, summary)

if __name__ == "__main__":
    mcp.run()
