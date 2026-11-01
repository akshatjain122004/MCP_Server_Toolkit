from servers.hello.server import add, greet


def test_greet_returns_friendly_message():
    assert greet("Akshat") == "Hello, Akshat!"


def test_add_returns_sum():
    assert add(2, 3) == 5
