import os
from dotenv import load_dotenv
from langchain_core.tools import tool
from pathlib import Path
from datetime import datetime
from langchain_core.prompts import PromptTemplate
from langchain.chat_models.base import init_chat_model

# ✅ FastMCP 서버의 구현 함수들을 임포트
from notion_mcp_server import _search_notion_impl, _get_page_content_impl, _update_page_impl
from github_mcp_server import (
    _github_search_repo_impl, 
    _github_list_my_repos_impl, 
    _github_list_org_repos_impl,
    _github_readme_impl, 
    _github_list_paths_impl, 
    _github_get_file_impl
)
from slack_mcp_server import _slack_post_message_impl
from discord_mcp_server import _discord_post_message_impl

# ✅ 동기화 도구 임포트
from sync_tools import (
    check_sync_status,
    full_sync_notion,
    incremental_sync_notion,
    auto_sync_after_notion_action
)

load_dotenv()

# --- Notion ---
@tool
def notion_search(query: str) -> dict:
    """
    Notion 워크스페이스에서 특정 키워드를 포함하는 페이지나 데이터베이스를 검색합니다.
    회의록, 프로젝트 문서, 기획안 등을 찾을 때 유용합니다.
    """
    print(f"--- Notion 검색 실행: {query} ---")
    return _search_notion_impl(query)

@tool
def notion_get_page_content(page_id: str) -> dict:
    """
    Notion 페이지의 내용을 가져옵니다.
    """
    return _get_page_content_impl(page_id)

@tool
def notion_update_page(page_id: str, summary: str) -> dict:
    """
    Notion 페이지의 내용을 업데이트합니다.
    """
    return _update_page_impl(page_id, summary)

# --- GitHub ---
@tool
def github_search_repo(repo_name: str) -> dict:
    """
    저장소 이름으로 GitHub 전체에서 공개 저장소를 검색합니다.
    """
    print(f"--- GitHub 저장소 검색: {repo_name} ---")
    return _github_search_repo_impl(repo_name)

@tool
def github_list_my_repos(visibility: str = "all") -> dict:
    """
    현재 인증된 사용자(GITHUB_API_TOKEN 소유자)의 저장소 목록을 반환합니다.
    Args:
        visibility: "all", "public", "private"
    """
    print(f"--- 내 저장소 목록 조회: {visibility} ---")
    return _github_list_my_repos_impl(visibility)

@tool
def github_list_org_repos(org_name: str) -> dict:
    """
    특정 조직(organization)의 저장소 목록을 반환합니다.
    Args:
        org_name: 조직 이름 (예: "SSAFY-S13P31A404")
    """
    print(f"--- 조직 저장소 목록 조회: {org_name} ---")
    return _github_list_org_repos_impl(org_name)

@tool
def github_readme_tool(repo_full_name: str) -> dict:
    """
    GitHub 저장소의 README 파일 내용을 가져옵니다.
    """
    return _github_readme_impl(repo_full_name)

@tool
def github_list_paths_tool(repo_full_name: str, path: str = "") -> dict:
    """
    GitHub 저장소에서 특정 경로의 파일 및 디렉토리 목록을 가져옵니다.
    """
    return _github_list_paths_impl(repo_full_name, path)

@tool
def github_get_file_tool(repo_full_name: str, path: str) -> dict:
    """
    GitHub 저장소에서 특정 파일의 내용을 가져옵니다.
    """
    return _github_get_file_impl(repo_full_name, path)

# --- Slack / Discord ---
@tool
def slack_post_tool(channel: str, text: str) -> dict:
    """
    Slack 채널에 메시지를 전송합니다.
    """
    return _slack_post_message_impl(channel, text)

@tool
def discord_post_tool(text: str, webhook_url: str = "") -> dict:
    """
    Discord 웹훅을 사용하여 메시지를 전송합니다.
    """
    return _discord_post_message_impl(text, webhook_url)

# --- LLM 초기화 (문서 생성용) ---
_llm_instance = None

def _get_llm():
    global _llm_instance
    if _llm_instance is None:
        model_name = os.getenv("OPENAI_MODEL", "gpt-5")
        model_provider = os.getenv("MODEL_PROVIDER", "openai")
        _llm_instance = init_chat_model(model_name, model_provider=model_provider)
    return _llm_instance

# --- 문서 타입별 템플릿 로더 ---
def _load_template(doc_type: str) -> str:
    """문서 타입에 맞는 프롬프트 템플릿 로드"""
    mapping = {
        "회의록": "meeting_template.txt",
        "기술 회의": "tech_review_template.txt",
        "회고록": "retrospective_template.txt",
    }
    template_file = mapping.get(doc_type, "meeting_template.txt")
    template_path = Path(__file__).parent / "prompts" / template_file
    
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    
    # 폴백 템플릿
    return f"""다음 {doc_type} 내용을 요약하고 정리해주세요.

{{context}}

위 내용을 바탕으로 다음 형식으로 정리해주세요:
- 주요 내용
- 결정 사항
- 액션 아이템"""

@tool
def render_markdown_by_type(doc_type: str, context: str) -> dict:
    """
    문서 유형(회의록/기술 회의/회고록)에 맞는 템플릿을 적용하여 마크다운을 생성합니다.
    Args:
        doc_type: "회의록", "기술 회의", "회고록" 중 하나
        context: 원본 문서 내용
    Returns:
        {"md_content": str} - 생성된 마크다운 내용
    """
    print(f"--- 문서 렌더링 실행: {doc_type}, 내용 길이: {len(context)} ---")
    try:
        template_str = _load_template(doc_type)
        prompt = PromptTemplate(input_variables=["context"], template=template_str)
        formatted = prompt.format(context=context)
        
        llm = _get_llm()
        result = llm.invoke(formatted)
        return {"md_content": result.content}
    except Exception as e:
        return {"error": str(e), "md_content": ""}

@tool
def save_markdown_file(base_name: str, doc_type: str, md_content: str) -> dict:
    """
    생성된 마크다운 문서를 outputs/ 폴더에 저장합니다.
    Args:
        base_name: 파일 이름 베이스 (예: "회의록")
        doc_type: 문서 타입 (예: "회의록")
        md_content: 저장할 마크다운 내용
    Returns:
        {"saved_path": str, "preview": str} - 저장된 파일 경로와 미리보기
    """
    print(f"--- 마크다운 파일 저장: {base_name}, {doc_type} ---")
    try:
        out_dir = Path("outputs")
        out_dir.mkdir(exist_ok=True)
        
        filename = f"{base_name}_{doc_type}_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
        file_path = out_dir / filename
        
        file_path.write_text(md_content, encoding="utf-8")
        
        # 미리보기 (처음 500자)
        preview = md_content[:500] + ("..." if len(md_content) > 500 else "")
        
        return {
            "saved_path": str(file_path),
            "preview": preview,
            "success": True
        }
    except Exception as e:
        return {"error": str(e), "success": False}

# 컨텍스트별 도구 선택
def get_tools_for_context(context):
    """
    단일 또는 복합 컨텍스트에 맞는 도구 반환.
    context가 문자열이면 단일, 리스트면 복합.
    """
    # 리스트로 받은 경우 (복합 컨텍스트)
    if isinstance(context, list):
        tools = []
        seen_names = set()
        for ctx in context:
            ctx_tools = get_tools_for_context(ctx)
            for tool in ctx_tools:
                tool_name = tool.name if hasattr(tool, 'name') else str(tool)
                if tool_name not in seen_names:
                    seen_names.add(tool_name)
                    tools.append(tool)
        return tools
    
    # 문자열로 받은 경우 (단일 컨텍스트)
    if context == "notion":
        return [
            notion_search, notion_get_page_content, notion_update_page,
            render_markdown_by_type, save_markdown_file
        ]
    if context == "github":
        return [
            github_search_repo,
            github_list_my_repos,
            github_list_org_repos,
            github_readme_tool, 
            github_list_paths_tool, 
            github_get_file_tool
        ]
    if context == "slack_discord":
        return [slack_post_tool, discord_post_tool]
    if context == "sync":
        return [
            check_sync_status,
            full_sync_notion,
            incremental_sync_notion,
            auto_sync_after_notion_action
        ]
    if context == "multi":
        return all_tools
    return []

# ✅ 동기화 도구 추가
sync_tools = [
    check_sync_status,
    full_sync_notion,
    incremental_sync_notion,
    auto_sync_after_notion_action
]

# 전체 도구 모음 (동기화 도구 포함)
all_tools = [
    notion_search, notion_get_page_content, notion_update_page,
    github_search_repo, github_list_my_repos, github_list_org_repos,
    github_readme_tool, github_list_paths_tool, github_get_file_tool,
    slack_post_tool, discord_post_tool,
    render_markdown_by_type, save_markdown_file
] + sync_tools