import functools
import inspect
import logging
import sys
import time

_SECRET_KEY_HINTS = ("token", "key", "secret", "password", "authorization")


def get_logger(name: str) -> logging.Logger:
    """Return a logger that writes to stderr.

    MCP servers talk to clients over stdout, so application logs must
    never go there — stderr is the only safe stream for them.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def _redact(kwargs: dict) -> dict:
    """Replace any value whose key name looks secret-ish with a placeholder."""
    return {
        key: "***" if any(hint in key.lower() for hint in _SECRET_KEY_HINTS) else value
        for key, value in kwargs.items()
    }


def audit(logger: logging.Logger):
    """Decorator: log tool name, arguments, duration (ms) and outcome for every call.

    Wraps a sync or async tool function so each invocation produces exactly one
    audit line on stderr, whether it succeeds or raises. Argument values whose
    keyword name looks secret-ish (token, key, secret, password, authorization)
    are redacted before logging.
    """

    def decorator(func):
        name = func.__name__

        def _line(status: str, duration_ms: float, kwargs: dict) -> None:
            logger.info(
                "audit tool=%s status=%s duration_ms=%.1f args=%r",
                name,
                status,
                duration_ms,
                _redact(kwargs),
            )

        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start = time.monotonic()
                try:
                    result = await func(*args, **kwargs)
                except Exception:
                    _line("error", (time.monotonic() - start) * 1000, kwargs)
                    raise
                _line("ok", (time.monotonic() - start) * 1000, kwargs)
                return result

            return async_wrapper

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.monotonic()
            try:
                result = func(*args, **kwargs)
            except Exception:
                _line("error", (time.monotonic() - start) * 1000, kwargs)
                raise
            _line("ok", (time.monotonic() - start) * 1000, kwargs)
            return result

        return sync_wrapper

    return decorator
