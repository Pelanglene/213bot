"""Handlers package"""

from telegram.ext import Application

from .basic import register_basic_handlers
from .ping import register_ping_handlers


def register_all_handlers(app: Application) -> None:
    """
    Register all bot handlers

    Args:
        app: Telegram application instance
    """
    register_basic_handlers(app)
    register_ping_handlers(app)


__all__ = ["register_all_handlers"]
