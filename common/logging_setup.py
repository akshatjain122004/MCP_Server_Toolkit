import logging
import sys


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
