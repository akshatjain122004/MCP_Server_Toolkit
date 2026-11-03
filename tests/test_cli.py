from common.cli import http_port


def test_http_port_returns_default_when_no_flag(monkeypatch):
    monkeypatch.setattr("sys.argv", ["server.py", "--http"])
    assert http_port(8000) == 8000


def test_http_port_returns_explicit_value(monkeypatch):
    monkeypatch.setattr("sys.argv", ["server.py", "--http", "--port", "9100"])
    assert http_port(8000) == 9100
