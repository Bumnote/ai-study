import os
from dotenv import load_dotenv
from fastmcp import FastMCP
from slack_sdk import WebClient
from typing import Optional, List, Dict

load_dotenv()

mcp = FastMCP("Slack MCP Server")

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
DEFAULT_SUMMARY_CHANNEL = os.getenv("DEFAULT_SUMMARY_CHANNEL", "#general")

# ✅ 코어 함수 정의 (데코레이터 없이)
def _slack_post_message_impl(channel: str, text: str) -> dict:
    """Slack 채널로 메시지를 전송 (구현부)
    지정된 채널이 없거나 전송에 실패하면 DEFAULT_SUMMARY_CHANNEL로 폴백합니다.
    """
    if not SLACK_BOT_TOKEN:
        return {"dry_run": True, "channel": channel or DEFAULT_SUMMARY_CHANNEL, "text": text[:2000]}

    target = channel or DEFAULT_SUMMARY_CHANNEL
    try:
        client = WebClient(token=SLACK_BOT_TOKEN)
        resp = client.chat_postMessage(channel=target, text=text)
        if resp.get("ok"):
            return {"ok": True, "ts": resp["ts"], "channel": target}
        # 지정 채널 전송 실패 시 기본 채널로 폴백 시도
        if target != DEFAULT_SUMMARY_CHANNEL:
            try:
                resp2 = client.chat_postMessage(channel=DEFAULT_SUMMARY_CHANNEL, text=text)
                if resp2.get("ok"):
                    return {
                        "ok": True,
                        "ts": resp2["ts"],
                        "channel": DEFAULT_SUMMARY_CHANNEL,
                        "fallback": True,
                        "original_channel": target,
                    }
                return {"ok": False, "response": resp2.data, "tried": [target, DEFAULT_SUMMARY_CHANNEL]}
            except Exception as e2:
                return {"error": f"Slack 전송 중 문제(폴백 시도 포함): {e2}", "original_response": resp.data}
        return {"ok": False, "response": resp.data}
    except Exception as e:
        # 예외 발생 시 기본 채널로 마지막 폴백 시도
        try:
            client = WebClient(token=SLACK_BOT_TOKEN)
            resp2 = client.chat_postMessage(channel=DEFAULT_SUMMARY_CHANNEL, text=text)
            if resp2.get("ok"):
                return {
                    "ok": True,
                    "ts": resp2["ts"],
                    "channel": DEFAULT_SUMMARY_CHANNEL,
                    "fallback": True,
                    "original_channel": channel,
                }
            return {"error": f"Slack 전송 중 문제: {e}", "fallback_response": resp2.data}
        except Exception as e2:
            return {"error": f"Slack 전송 중 문제: {e}; 폴백 실패: {e2}"}

# ✅ FastMCP 도구로 등록
@mcp.tool
def slack_post_message(channel: str, text: str) -> dict:
    """
    Slack 채널로 메시지를 전송합니다. 채널 예: '#backend'
    채널을 지정하지 않거나 지정 채널 전송 실패 시 DEFAULT_SUMMARY_CHANNEL (기본 '#general')로 폴백합니다.
    채널 선택은 slack_list_channels로 목록을 확인한 뒤 사용하세요.
    토큰이 없으면 드라이런으로 동작합니다.
    """
    return _slack_post_message_impl(channel, text)

# ------------------ 추가되는 코드 ------------------

def _slack_list_channels_impl(types: str = "public_channel,private_channel") -> dict:
    """Slack 워크스페이스의 채널 목록을 반환합니다.
    types: conversations.list에 전달할 types 문자열 (예: "public_channel,private_channel")
    반환: {'ok': True, 'channels': [{'id':..., 'name':..., 'is_private':...}, ...]} 또는 오류 정보
    """
    if not SLACK_BOT_TOKEN:
        # dry run: 예시 채널 반환
        return {"dry_run": True, "channels": [{"id": "C123", "name": "general", "is_private": False}, {"id": "C456", "name": "random", "is_private": False}]}

    try:
        client = WebClient(token=SLACK_BOT_TOKEN)
        channels: List[Dict] = []
        cursor: Optional[str] = None
        while True:
            resp = client.conversations_list(types=types, cursor=cursor, limit=200)
            if not resp.get("ok"):
                return {"ok": False, "error": resp.data}
            for ch in resp.get("channels", []):
                channels.append({
                    "id": ch.get("id"),
                    "name": ch.get("name"),
                    "is_private": ch.get("is_private", False),
                })
            cursor = resp.get("response_metadata", {}).get("next_cursor") or None
            if not cursor:
                break
        return {"ok": True, "channels": channels}
    except Exception as e:
        return {"ok": False, "error": f"Slack 채널 조회 중 문제: {e}"}

@mcp.tool
def slack_list_channels(types: str = "public_channel,private_channel") -> dict:
    """
    워크스페이스의 채널 목록을 반환합니다.
    types: conversations.list에 넘길 types (기본: public_channel,private_channel)
    사용 예: 호출로 얻은 리스트에서 채널 id 또는 '#이름'을 선택해 slack_post_message로 전송하세요.
    """
    return _slack_list_channels_impl(types)
# ------------------ 추가 끝 ------------------