"""Middleware to track active users in group chats"""

import logging
from collections import defaultdict, deque

from telegram import Chat, Update
from telegram.ext import Application, TypeHandler

logger = logging.getLogger(__name__)

# Maximum number of recent users to track per chat
MAX_RECENT_USERS = 100


class UserTrackerMiddleware:
    """Track active users in group chats for kill_random command"""

    def __init__(self):
        """Initialize user tracker"""
        self._recent_users: dict[int, deque] = defaultdict(
            lambda: deque(maxlen=MAX_RECENT_USERS)
        )

    async def track_user(self, update: Update, context) -> None:
        """
        Track user activity in group chats

        Args:
            update: Telegram update
            context: Callback context
        """
        if not update.effective_chat or not update.effective_user:
            return

        chat = update.effective_chat
        user = update.effective_user

        # Only track in group chats
        if chat.type not in [Chat.GROUP, Chat.SUPERGROUP]:
            return

        # Don't track bots
        if user.is_bot:
            return

        chat_id = chat.id
        user_id = user.id

        # Add user to recent users if not already present
        if user_id not in self._recent_users[chat_id]:
            self._recent_users[chat_id].append(user_id)
            logger.debug(
                f"Tracked user {user_id} in chat {chat_id}. "
                f"Total tracked: {len(self._recent_users[chat_id])}"
            )

        # Update context.chat_data for easy access in handlers
        if "recent_users" not in context.chat_data:
            context.chat_data["recent_users"] = []

        if user_id not in context.chat_data["recent_users"]:
            context.chat_data["recent_users"].append(user_id)

            # Limit the size
            if len(context.chat_data["recent_users"]) > MAX_RECENT_USERS:
                context.chat_data["recent_users"] = context.chat_data["recent_users"][
                    -MAX_RECENT_USERS:
                ]

    def get_recent_users(self, chat_id: int) -> list[int]:
        """
        Get list of recent users in a chat

        Args:
            chat_id: Chat ID

        Returns:
            List of user IDs
        """
        return list(self._recent_users[chat_id])


# Global instance
user_tracker = UserTrackerMiddleware()


def register_user_tracker(app: Application) -> None:
    """
    Register user tracker middleware

    Args:
        app: Telegram application instance
    """
    # Add handler to track all updates
    app.add_handler(
        TypeHandler(Update, user_tracker.track_user),
        group=-1,  # Run before other handlers
    )
    logger.info("User tracker middleware registered")
