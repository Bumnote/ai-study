import os
from typing import List
from dotenv import load_dotenv
from fastmcp import FastMCP
from github import Github
from github.GithubException import UnknownObjectException

load_dotenv()
mcp = FastMCP("GitHub MCP Server")

def _get_github():
    token = os.getenv("GITHUB_API_TOKEN")
    # Allow anonymous usage for fewer setup steps (rate-limited by GitHub).
    return Github(token) if token else Github()

# ✅ 코어 함수 정의 (데코레이터 없이)
def _github_search_repo_impl(repo_name: str) -> dict:
    """저장소 이름으로 GitHub 검색 (구현부) - 전체 공개 저장소"""
    try:
        g = _get_github()
        repos = g.search_repositories(query=repo_name, sort="stars", order="desc")
        
        results = []
        for repo in repos[:5]:
            results.append({
                "full_name": repo.full_name,
                "description": repo.description or "설명 없음",
                "stars": repo.stargazers_count,
                "url": repo.html_url,
                "private": repo.private
            })
        
        return {"results": results, "count": len(results)}
    except Exception as e:
        return {"error": str(e), "results": []}

def _github_list_my_repos_impl(visibility: str = "all") -> dict:
    """현재 인증된 사용자의 저장소 목록 (구현부)"""
    try:
        g = _get_github()
        user = g.get_user()
        
        # visibility: "all", "public", "private"
        repos = user.get_repos(type="owner", sort="updated", direction="desc")
        
        results = []
        for repo in repos[:20]:  # 최근 업데이트된 20개
            if visibility == "all" or \
               (visibility == "public" and not repo.private) or \
               (visibility == "private" and repo.private):
                results.append({
                    "full_name": repo.full_name,
                    "description": repo.description or "설명 없음",
                    "private": repo.private,
                    "url": repo.html_url,
                    "updated_at": repo.updated_at.isoformat() if repo.updated_at else None
                })
        
        return {
            "user": user.login,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        return {"error": str(e), "results": []}

def _github_list_org_repos_impl(org_name: str) -> dict:
    """특정 조직의 저장소 목록 (구현부)"""
    try:
        g = _get_github()
        org = g.get_organization(org_name)
        
        repos = org.get_repos(type="all", sort="updated", direction="desc")
        
        results = []
        for repo in repos[:20]:
            results.append({
                "full_name": repo.full_name,
                "description": repo.description or "설명 없음",
                "private": repo.private,
                "url": repo.html_url,
                "updated_at": repo.updated_at.isoformat() if repo.updated_at else None
            })
        
        return {
            "organization": org_name,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        return {"error": str(e), "results": []}

def _github_readme_impl(repo_full_name: str) -> dict:
    """해당 저장소의 기본 README 내용을 텍스트로 반환 (구현부)"""
    try:
        g = _get_github()
        repo = g.get_repo(repo_full_name)
        readme = repo.get_readme()
        content = readme.decoded_content.decode("utf-8", errors="replace")
        return {"repo": repo_full_name, "readme": content}
    except UnknownObjectException:
        return {"error": f"'{repo_full_name}' 저장소 또는 README를 찾을 수 없습니다."}
    except Exception as e:
        return {"error": f"GitHub API 통신 문제: {e}"}

def _github_list_paths_impl(repo_full_name: str, path: str = "") -> dict:
    """주어진 경로(디렉토리)의 파일/폴더 목록을 반환 (구현부)"""
    try:
        g = _get_github()
        repo = g.get_repo(repo_full_name)
        items = repo.get_contents(path or "")
        if not isinstance(items, list):
            return {"repo": repo_full_name, "path": items.path, "type": items.type}
        entries = [{"type": it.type, "path": it.path} for it in items]
        return {"repo": repo_full_name, "path": path or "", "items": entries}
    except UnknownObjectException:
        return {"error": f"'{repo_full_name}' 또는 경로 '{path}' 를 찾을 수 없습니다."}
    except Exception as e:
        return {"error": f"GitHub API 통신 문제: {e}"}

def _github_get_file_impl(repo_full_name: str, path: str) -> dict:
    """파일 내용을 반환 (구현부)"""
    try:
        g = _get_github()
        repo = g.get_repo(repo_full_name)
        file_or_dir = repo.get_contents(path)
        if isinstance(file_or_dir, list):
            entries = [{"type": it.type, "path": it.path} for it in file_or_dir]
            return {"repo": repo_full_name, "path": path, "is_directory": True, "items": entries}
        content = file_or_dir.decoded_content.decode("utf-8", errors="replace")
        return {"repo": repo_full_name, "path": path, "is_directory": False, "content": content}
    except UnknownObjectException:
        return {"error": f"'{repo_full_name}' 또는 파일 '{path}' 를 찾을 수 없습니다."}
    except Exception as e:
        return {"error": f"GitHub API 통신 문제: {e}"}

# ✅ FastMCP 도구로 등록
@mcp.tool
def github_search_repo(repo_name: str) -> dict:
    """
    저장소 이름으로 GitHub 전체에서 공개 저장소를 검색합니다.
    Args:
        repo_name: 검색할 저장소 이름 (예: "catchTable")
    Returns:
        {"results": [{"full_name": "owner/repo", ...}]}
    """
    return _github_search_repo_impl(repo_name)

@mcp.tool
def github_list_my_repos(visibility: str = "all") -> dict:
    """
    현재 인증된 사용자의 저장소 목록을 반환합니다.
    Args:
        visibility: "all" (전체), "public" (공개), "private" (비공개)
    Returns:
        {"user": str, "results": [{"full_name": "owner/repo", "private": bool, ...}]}
    """
    return _github_list_my_repos_impl(visibility)

@mcp.tool
def github_list_org_repos(org_name: str) -> dict:
    """
    특정 조직(organization)의 저장소 목록을 반환합니다.
    Args:
        org_name: 조직 이름 (예: "facebook", "SSAFY-S13P31A404")
    Returns:
        {"organization": str, "results": [{"full_name": "org/repo", ...}]}
    """
    return _github_list_org_repos_impl(org_name)

@mcp.tool
def github_readme(repo_full_name: str) -> dict:
    """해당 저장소의 기본 README 내용을 텍스트로 반환합니다. 예: 'owner/repo'"""
    return _github_readme_impl(repo_full_name)

@mcp.tool
def github_list_paths(repo_full_name: str, path: str = "") -> dict:
    """주어진 경로(디렉토리)의 파일/폴더 목록을 반환합니다. path가 비면 루트."""
    return _github_list_paths_impl(repo_full_name, path)

@mcp.tool
def github_get_file(repo_full_name: str, path: str) -> dict:
    """파일 내용을 반환합니다. path 예: 'src/main.py'"""
    return _github_get_file_impl(repo_full_name, path)

if __name__ == "__main__":
    mcp.run()
