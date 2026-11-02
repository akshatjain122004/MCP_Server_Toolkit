import httpx
import pytest
import respx
from mcp.server.mcpserver.exceptions import ToolError

from servers.github_analyzer.server import (
    GITHUB_API_BASE,
    get_repo_summary,
    list_open_issues,
    recent_commits,
)

REPO_JSON = {
    "full_name": "pallets/flask",
    "description": "The Python micro framework for building web applications.",
    "stargazers_count": 68000,
    "forks_count": 16000,
    "language": "Python",
    "open_issues_count": 5,
    "updated_at": "2026-01-01T00:00:00Z",
}

SEARCH_ISSUES_JSON = {
    "total_count": 1,
    "items": [
        {
            "number": 1,
            "title": "A real issue",
            "labels": [{"name": "bug"}],
            "html_url": "https://github.com/pallets/flask/issues/1",
        }
    ],
}

COMMITS_JSON = [
    {
        "sha": "abcdef1234567890",
        "commit": {
            "message": "Fix the thing\n\nLonger explanation here.",
            "author": {"name": "Jane Doe", "date": "2026-01-01T00:00:00Z"},
        },
    }
]


@pytest.mark.asyncio
@respx.mock
async def test_get_repo_summary_returns_expected_keys():
    respx.get(f"{GITHUB_API_BASE}/repos/pallets/flask").mock(
        return_value=httpx.Response(200, json=REPO_JSON)
    )
    result = await get_repo_summary("pallets", "flask")
    assert result == {
        "full_name": "pallets/flask",
        "description": REPO_JSON["description"],
        "stars": 68000,
        "forks": 16000,
        "language": "Python",
        "open_issues": 5,
        "updated_at": "2026-01-01T00:00:00Z",
    }


@pytest.mark.asyncio
@respx.mock
async def test_list_open_issues_excludes_pull_requests():
    route = respx.get(f"{GITHUB_API_BASE}/search/issues").mock(
        return_value=httpx.Response(200, json=SEARCH_ISSUES_JSON)
    )
    result = await list_open_issues("pallets", "flask")
    assert len(result) == 1
    assert result[0]["number"] == 1
    assert result[0]["labels"] == ["bug"]
    # type:issue excludes PRs server-side, so the query itself carries that constraint.
    assert "type:issue" in route.calls.last.request.url.params["q"]


@pytest.mark.asyncio
@respx.mock
async def test_list_open_issues_finds_issue_buried_behind_many_prs():
    # Regression: on an active repo the most recently created items are often all
    # PRs (e.g. fastapi/fastapi: 59 of its 60 "open issues" are PRs). A naive
    # fetch-one-page-then-filter approach can return an empty list even though
    # real issues exist. Search with type:issue must not have this problem.
    respx.get(f"{GITHUB_API_BASE}/search/issues").mock(
        return_value=httpx.Response(
            200,
            json={
                "total_count": 1,
                "items": [
                    {
                        "number": 10370,
                        "title": "The one real issue",
                        "labels": [],
                        "html_url": "https://github.com/fastapi/fastapi/issues/10370",
                    }
                ],
            },
        )
    )
    result = await list_open_issues("fastapi", "fastapi")
    assert len(result) == 1
    assert result[0]["number"] == 10370


@pytest.mark.asyncio
@respx.mock
async def test_recent_commits_trims_message_and_sha():
    respx.get(f"{GITHUB_API_BASE}/repos/pallets/flask/commits").mock(
        return_value=httpx.Response(200, json=COMMITS_JSON)
    )
    result = await recent_commits("pallets", "flask")
    assert result == [
        {
            "sha": "abcdef1",
            "message": "Fix the thing",
            "author": "Jane Doe",
            "date": "2026-01-01T00:00:00Z",
        }
    ]


@pytest.mark.asyncio
@respx.mock
async def test_404_produces_friendly_message():
    respx.get(f"{GITHUB_API_BASE}/repos/pallets/doesnotexist").mock(
        return_value=httpx.Response(404, json={"message": "Not Found"})
    )
    with pytest.raises(ToolError, match="Repository not found"):
        await get_repo_summary("pallets", "doesnotexist")


@pytest.mark.asyncio
@respx.mock
async def test_403_produces_friendly_rate_limit_message():
    respx.get(f"{GITHUB_API_BASE}/repos/pallets/flask").mock(
        return_value=httpx.Response(403, json={"message": "rate limited"})
    )
    with pytest.raises(ToolError, match="rate limit"):
        await get_repo_summary("pallets", "flask")
