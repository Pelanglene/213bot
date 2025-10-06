"""Logging configuration"""

import logging
import sys
from typing import Optional


def setup_logger(name: Optional[str] = None, level: str = "INFO") -> logging.Logger:
    """
    Configure and return logger

    Args:
        name: Logger name (default: root logger)
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, level.upper()))

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    return logger
