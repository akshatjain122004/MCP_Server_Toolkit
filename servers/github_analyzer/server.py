"""Phase 6: GitHub analyzer server — repo/PR/issue insights over MCP."""

import os
import sys
from pathlib import Path
from typing import Annotated, Any

import httpx
import uvicorn
from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import Field

# Running this file directly (as Claude Desktop does) only puts this file's own
# directory on sys.path, so the project-root `common` package needs a hand.
_PROJECT_ROOT = str(Path(__file__).parents[2])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from common.auth import ApiKeyMiddleware, require_api_key  # noqa: E402
from common.cli import http_port  # noqa: E402
from common.limits import RateLimiter  # noqa: E402
from common.logging_setup import audit, get_logger  # noqa: E402

DEFAULT_HTTP_PORT = 8001

load_dotenv()

logger = get_logger("github-analyzer")

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

GITHUB_API_BASE = "https://api.github.com"

mcp = MCPServer("github-analyzer")

github_limit = RateLimiter(max_calls=30, period=60)

OwnerField = Annotated[str, Field(pattern=r"^[A-Za-z0-9-]{1,39}$")]
RepoField = Annotated[str, Field(pattern=r"^[A-Za-z0-9._-]{1,100}$")]
LimitField = Annotated[int, Field(ge=1, le=30)]


async def gh(path: str, params: dict[str, Any] | None = None) -> Any:
    """Call the GitHub REST API and return the parsed JSON body, or raise a friendly ValueError."""
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{GITHUB_API_BASE}{path}", headers=headers, params=params
            )
    except httpx.TimeoutException:
        raise ToolError("GitHub did not respond in time.")

    if response.status_code == 404:
        raise ToolError("Repository not found. Check owner and repo name.")
    if response.status_code in (403, 429):
        raise ToolError("GitHub rate limit reached. Try again later.")
    response.raise_for_status()
    return response.json()


@mcp.tool()
@audit(logger)
async def get_repo_summary(owner: OwnerField, repo: RepoField) -> dict:
    """Get a short summary of a public GitHub repo: stars, forks, language and activity. Call this first to check a repo exists and is active."""
    github_limit.check()
    data = await gh(f"/repos/{owner}/{repo}")
    return {
        "full_name": data["full_name"],
        "description": data["description"],
        "stars": data["stargazers_count"],
        "forks": data["forks_count"],
        "language": data["language"],
        "open_issues": data["open_issues_count"],
        "updated_at": data["updated_at"],
    }


@mcp.tool()
@audit(logger)
async def list_open_issues(owner: OwnerField, repo: RepoField, limit: LimitField = 10) -> list[dict]:
    """List recent open issues (not pull requests) of a public repo, up to 30. Use after get_repo_summary to see what's being worked on.

    On active repos most recent activity is pull requests, so filtering a plain issues
    page can miss real issues entirely; this uses GitHub's issue search to exclude PRs
    at the source instead.
    """
    github_limit.check()
    limit = max(1, min(limit, 30))
    data = await gh(
        "/search/issues",
        params={
            "q": f"repo:{owner}/{repo} type:issue state:open",
            "sort": "created",
            "order": "desc",
            "per_page": limit,
        },
    )
    return [
        {
            "number": item["number"],
            "title": item["title"],
            "labels": [label["name"] for label in item["labels"]],
            "url": item["html_url"],
        }
        for item in data["items"]
    ]


@mcp.tool()
@audit(logger)
async def recent_commits(owner: OwnerField, repo: RepoField, limit: LimitField = 10) -> list[dict]:
    """List recent commits on the default branch of a public repo, up to 30. Commit messages are trimmed to their first line."""
    github_limit.check()
    limit = max(1, min(limit, 30))
    data = await gh(
        f"/repos/{owner}/{repo}/commits",
        params={"per_page": limit},
    )
    return [
        {
            "sha": item["sha"][:7],
            "message": item["commit"]["message"].splitlines()[0],
            "author": (item["commit"]["author"] or {}).get("name"),
            "date": (item["commit"]["author"] or {}).get("date"),
        }
        for item in data
    ]


@mcp.prompt()
def analyse_repo(owner: OwnerField, repo: RepoField) -> str:
    """Ask for an analysis of a public repo: activity level, main issue themes and a health verdict."""
    return (
        f"Analyse the GitHub repo {owner}/{repo}:\n"
        "1. Activity level (commit frequency, recency).\n"
        "2. Main themes in the open issues.\n"
        "3. An overall health verdict."
    )


if __name__ == "__main__":
    if not GITHUB_TOKEN:
        logger.error("GITHUB_TOKEN is not set. Add it to .env before using this server.")
        sys.exit(1)
    if "--http" in sys.argv:
        require_api_key()
        app = mcp.streamable_http_app(host="0.0.0.0")
        app.add_middleware(ApiKeyMiddleware)
        uvicorn.run(app, host="0.0.0.0", port=http_port(DEFAULT_HTTP_PORT))
    else:
        mcp.run()
