# notion_mcp_server.py
"""
✅ Notion MCP Server
- 모든 페이지 메타데이터 수집
- 페이지 내용 조회
- 페이지 요약 추가
"""

import os
from fastmcp import FastMCP
from utils.notion_client import (
    get_all_pages_metadata,
    get_notion_client,
    extract_title
)

mcp = FastMCP("Notion MCP Server")

# ============================================================
# 📚 Notion Metadata Fetch
# ============================================================
@mcp.tool
def get_all_metadata() -> dict:
    """모든 Notion 페이지 및 데이터베이스의 메타데이터를 반환"""
    try:
        pages = get_all_pages_metadata()
        return {"count": len(pages), "results": pages}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# 🧠 Page Content Fetch
# ============================================================
@mcp.tool
def get_page_content(page_id: str) -> dict:
    """특정 페이지의 텍스트 콘텐츠를 추출"""
    try:
        client = get_notion_client()
        blocks = client.blocks.children.list(block_id=page_id)
        texts = []
        for b in blocks.get("results", []):
            for key, val in b.items():
                if isinstance(val, dict) and "rich_text" in val:
                    rich = val["rich_text"]
                    txt = "".join([t.get("plain_text", "") for t in rich])
                    if txt.strip():
                        texts.append(txt)
        return {"page_id": page_id, "text": "\n".join(texts)}
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# 🧩 Update Page with Summary
# ============================================================
@mcp.tool
def update_page_summary(page_id: str, summary: str) -> dict:
    """페이지 하단에 요약 문단 추가"""
    try:
        client = get_notion_client()
        client.blocks.children.append(
            block_id=page_id,
            children=[
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": summary}}]},
                }
            ],
        )
        return {"status": "updated", "page_id": page_id}
    except Exception as e:
        return {"error": str(e), "page_id": page_id}
