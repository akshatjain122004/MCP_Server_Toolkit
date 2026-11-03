import sys


def http_port(default: int) -> int:
    """Return the --http port: an explicit `--port <N>` argument, else `default`.

    Each server has its own default so they can all run in --http mode at
    once without colliding on the same port.
    """
    if "--port" in sys.argv:
        return int(sys.argv[sys.argv.index("--port") + 1])
    return default
