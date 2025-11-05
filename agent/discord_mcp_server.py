import os
import requests
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()
mcp = FastMCP("Discord MCP Server")

# 기본 Webhook URL (채널당 1개). 필요 시 파라미터로도 받을 수 있음.
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

# ✅ 코어 함수 정의 (데코레이터 없이)
def _discord_post_message_impl(text: str, webhook_url: str = "") -> dict:
    """Discord 채널(Webhook)로 메시지를 전송 (구현부)"""
    url = webhook_url or DISCORD_WEBHOOK_URL
    if not url:
        return {"dry_run": True, "text": text[:2000]}
    try:
        resp = requests.post(url, json={"content": text})
        if 200 <= resp.status_code < 300:
            return {"ok": True}
        return {"ok": False, "status": resp.status_code, "text": resp.text}
    except Exception as e:
        return {"error": f"Discord 전송 중 문제: {e}"}

# ✅ FastMCP 도구로 등록
@mcp.tool
def discord_post_message(text: str, webhook_url: str = "") -> dict:
    """
    Discord 채널(Webhook)로 메시지를 전송합니다.
    - webhook_url이 주어지면 이를 사용, 비어있으면 DISCORD_WEBHOOK_URL 사용.
    - 토큰/봇 연결 없이도 Webhook으로 간단히 테스트할 수 있습니다.
    """
    return _discord_post_message_impl(text, webhook_url)

if __name__ == "__main__":
    mcp.run()
