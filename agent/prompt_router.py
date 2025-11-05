# prompt_router.py
from typing import Literal, List
from pathlib import Path

# === 1️⃣ 프롬프트 템플릿 정의 === #
def _load_prompt(name: str) -> str:
    """프롬프트 파일이 없으면 기본 템플릿 반환"""
    p = Path(__file__).parent / "prompts" / f"{name}.txt"
    if p.exists():
        return p.read_text(encoding="utf-8")
    # 폴백 기본 프롬프트
    return f"You are a helpful assistant for {name} tasks. Answer in Korean."

MEETING_PROMPT = _load_prompt("meeting_prompt")
RETROSPECTIVE_PROMPT = _load_prompt("retrospective_prompt")
TECHNICAL_MEETING_PROMPT = _load_prompt("technical_meeting_prompt")
GITHUB_REVIEW_PROMPT = _load_prompt("github_review_prompt")
POST_TO_CHANNEL_PROMPT = _load_prompt("post_to_channel_prompt")
SYNC_PROMPT = _load_prompt("sync_prompt")  # ✅ 추가
CASUAL_PROMPT = _load_prompt("casual_prompt")

# === 2️⃣ 라우팅 함수 정의 === #

def detect_context(user_input: str) -> List[str]:
    """
    사용자의 입력 내용을 기반으로 어떤 MCP 서버를 사용할지 결정합니다.
    복합 요청(예: 회의록 요약 + 디스코드 전송)을 처리하기 위해 리스트 반환.
    """
    text = user_input.lower()
    contexts = []

    # ✅ 동기화 관련 (최우선 체크 - 명시적 요청)
    sync_keywords = [
        "동기화", "sync", "싱크", "최신", "업데이트", 
        "가져와", "임베딩", "embedding", "상태 확인"
    ]
    if any(k in text for k in sync_keywords):
        contexts.append("sync")
        # 동기화만 요청한 경우 다른 컨텍스트 무시
        if any(k in text for k in ["동기화해", "sync", "상태 확인", "전체 동기화"]):
            return contexts

    # 회의/회고/기술 관련 (Notion)
    notion_keywords = [
        "회의", "회고", "회의록", "기술 회의", "기술회의",
        "action item", "결정 사항", "노션", "notion",
        "안건", "회의 내용", "retrospective", "meeting"
    ]
    if any(k in text for k in notion_keywords):
        contexts.append("notion")

    # 코드 관련 (GitHub)
    github_keywords = [
        "코드", "readme", "리뷰", "리팩토링", "repository", 
        "레포", "git", "pull request", "pr", "issue", "commit",
        "github", "깃허브", "소스", "파일"
    ]
    if any(k in text for k in github_keywords):
        contexts.append("github")

    # 결과 전송 관련 (Slack/Discord)
    channel_keywords = [
        "전달", "공유", "보내", "슬랙", "디스코드", 
        "post", "share", "slack", "discord", "채널", "메시지"
    ]
    if any(k in text for k in channel_keywords):
        contexts.append("slack_discord")

    # 기본은 일상 대화
    if not contexts:
        contexts.append("casual")
    
    return contexts


def get_prompt_for_context(contexts: List[str]) -> str:
    """
    감지된 context(들)에 따라 적절한 프롬프트 템플릿 반환.
    복합 요청의 경우 가장 우선순위가 높은 프롬프트 선택하되, 추가 지시사항 포함.
    """
    # ✅ 동기화 전용 프롬프트
    if "sync" in contexts and len(contexts) == 1:
        return """You are a Notion synchronization assistant.

**AVAILABLE TOOLS:**
1. **check_sync_status()** - 현재 동기화 상태 확인
2. **full_sync_notion()** - 전체 동기화 (첫 실행 또는 전체 재동기화)
3. **incremental_sync_notion()** - 증분 동기화 (마지막 동기화 이후 변경사항만)

**YOUR WORKFLOW:**
1. Understand user request (전체/증분/상태확인)
2. Call appropriate sync tool ONCE
3. Provide formatted result in Korean

**RESPONSE FORMAT:**
```
✅ [동기화 타입] 완료!

📊 결과:
- 새 페이지: X개
- 업데이트: Y개
- 총 임베딩: Z개

[추가 메시지]
```

**CRITICAL: Call sync tool ONLY ONCE and immediately provide results.**

Answer in Korean."""
    
    # 복합 요청: notion + slack_discord
    if "notion" in contexts and "slack_discord" in contexts:
        return """You are a helpful assistant that processes Notion documents and shares them.

**YOUR WORKFLOW:**
1. Search Notion: Use notion_search(query)
2. Get Content: Use notion_get_page_content(page_id)
3. Generate Summary: Use render_markdown_by_type(doc_type, context)
4. Save File: Use save_markdown_file(base_name, doc_type, md_content)
5. Share: Use discord_post_tool(text) or slack_post_tool(channel, text)

**After completing all tools, PROVIDE FINAL RESPONSE:**
```
✅ 처리 완료

📄 문서: [제목] ([타입])
💾 저장: [경로]
📨 전송: [채널]

📝 요약:
[내용 미리보기]
```

**THEN STOP. Do not call more tools.**

Answer in Korean."""
    
    # github + slack_discord
    if "github" in contexts and "slack_discord" in contexts:
        return """You are a helpful assistant that reviews GitHub code and shares results.

**YOUR WORKFLOW:**
1. Repository Info: github_search_repo() or github_list_my_repos()
2. Fetch README: github_readme_tool()
3. Share: discord_post_tool() or slack_post_tool()

**Maximum 5-6 tool calls. After getting info, STOP and provide summary.**

Answer in Korean."""
    
    # 단일 컨텍스트 프롬프트
    prompt_map = {
        "notion": """You are a Notion document processing assistant.

**WORKFLOW:**
1. notion_search(query) - ONCE
2. notion_get_page_content(page_id) - ONCE
3. render_markdown_by_type(doc_type, context) - ONCE
4. save_markdown_file(base_name, doc_type, md_content) - ONCE

**Total 4-5 tool calls maximum.**

**After save_markdown_file, provide final response:**
```
✅ 문서 처리 완료

📄 [제목] ([타입])
💾 [저장 경로]

📝 [미리보기]
```

**STOP after this response.**

Answer in Korean.""",
        
        "github": """You are a GitHub repository analysis assistant.

**TOOLS:**
1. **github_search_repo(name)** - Search public repos
2. **github_list_my_repos(visibility)** - List user's repos
3. **github_list_org_repos(org)** - List org's repos
4. **github_readme_tool(owner/repo)** - Get README
5. **github_list_paths_tool(owner/repo, path)** - Browse files
6. **github_get_file_tool(owner/repo, path)** - Read file

**EXAMPLES:**
- "내 저장소 찾아줘" → github_list_my_repos("all")
- "조직 저장소 보여줘" → github_list_org_repos("org-name")
- "저장소 검색" → github_search_repo("name")

**Maximum 3-4 tool calls. STOP and summarize.**

Answer in Korean.""",
        
        "slack_discord": POST_TO_CHANNEL_PROMPT,
        "sync": SYNC_PROMPT,
        "casual": CASUAL_PROMPT
    }
    
    return prompt_map.get(contexts[0], CASUAL_PROMPT)


def route_prompt(user_input: str) -> dict:
    """
    최종적으로 LangGraph Agent에 전달할 라우팅 정보 반환.
    """
    contexts = detect_context(user_input)
    prompt = get_prompt_for_context(contexts)
    
    # UI 호환성을 위해 primary context (첫 번째) 반환
    return {
        "context": contexts[0] if len(contexts) == 1 else "multi",
        "contexts": contexts,  # 모든 컨텍스트 리스트
        "prompt": prompt,
        "user_input": user_input
    }