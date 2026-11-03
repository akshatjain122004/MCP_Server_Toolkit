import os
import secrets

from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

PLACEHOLDER_API_KEY = "change-me"


class ApiKeyMiddleware(BaseHTTPMiddleware):
    """Reject requests whose `Authorization: Bearer <key>` doesn't match MCP_API_KEY."""

    async def dispatch(self, request: Request, call_next):
        expected = os.environ["MCP_API_KEY"]
        header = request.headers.get("authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not secrets.compare_digest(token, expected):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


def require_api_key() -> None:
    """Exit the process if MCP_API_KEY is missing or still the placeholder.

    Call this before serving HTTP mode — stdio mode never calls it, since it
    has no network exposure to protect. Loads `.env` itself, since not every
    server's entry point does.
    """
    load_dotenv()
    key = os.environ.get("MCP_API_KEY")
    if not key or key == PLACEHOLDER_API_KEY:
        raise SystemExit(
            "MCP_API_KEY is not set (or still 'change-me'). "
            "Set a real value in .env before running in --http mode."
        )
