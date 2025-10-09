"""Handlers package"""

from telegram.ext import Application

from .basic import register_basic_handlers
from .dead_chat import register_dead_chat_handlers
from .permissions import register_permissions_handlers
from .ping import register_ping_handlers
from .goon import register_goon_handlers


def register_all_handlers(app: Application) -> None:
    """
    Register all bot handlers

    Args:
        app: Telegram application instance
    """
    register_basic_handlers(app)
    register_ping_handlers(app)
    register_permissions_handlers(app)
    register_dead_chat_handlers(app)
    register_goon_handlers(app)


__all__ = ["register_all_handlers"]
