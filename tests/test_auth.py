import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from common.auth import ApiKeyMiddleware, require_api_key


def _make_client(monkeypatch, api_key: str) -> TestClient:
    monkeypatch.setenv("MCP_API_KEY", api_key)

    async def ok(request):
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/", ok)])
    app.add_middleware(ApiKeyMiddleware)
    return TestClient(app)


def test_request_without_auth_header_is_rejected(monkeypatch):
    client = _make_client(monkeypatch, "secret123")
    response = client.get("/")
    assert response.status_code == 401
    assert response.json() == {"error": "unauthorized"}


def test_request_with_wrong_key_is_rejected(monkeypatch):
    client = _make_client(monkeypatch, "secret123")
    response = client.get("/", headers={"Authorization": "Bearer wrong"})
    assert response.status_code == 401


def test_request_with_non_bearer_scheme_is_rejected(monkeypatch):
    client = _make_client(monkeypatch, "secret123")
    response = client.get("/", headers={"Authorization": "Basic secret123"})
    assert response.status_code == 401


def test_request_with_correct_key_succeeds(monkeypatch):
    client = _make_client(monkeypatch, "secret123")
    response = client.get("/", headers={"Authorization": "Bearer secret123"})
    assert response.status_code == 200
    assert response.text == "ok"


def _stub_out_dotenv_loading(monkeypatch):
    """Stop require_api_key() from reading the repo's real .env in tests."""
    monkeypatch.setattr("common.auth.load_dotenv", lambda: None)


def test_require_api_key_exits_when_unset(monkeypatch):
    _stub_out_dotenv_loading(monkeypatch)
    monkeypatch.delenv("MCP_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        require_api_key()


def test_require_api_key_exits_when_placeholder(monkeypatch):
    _stub_out_dotenv_loading(monkeypatch)
    monkeypatch.setenv("MCP_API_KEY", "change-me")
    with pytest.raises(SystemExit):
        require_api_key()


def test_require_api_key_passes_when_set_to_a_real_value(monkeypatch):
    _stub_out_dotenv_loading(monkeypatch)
    monkeypatch.setenv("MCP_API_KEY", "secret123")
    require_api_key()
