import logging


def get_logger(name: str) -> logging.Logger:
    """Return a named logger using the application-wide configuration."""
    return logging.getLogger(name)
