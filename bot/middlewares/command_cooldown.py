"""Global command cooldown middleware"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


class CommandCooldownService:
    """Service to track global and per-chat command cooldowns"""

    def __init__(self):
        self._last_used: Dict[str, datetime] = {}
        self.moscow_tz = ZoneInfo("Europe/Moscow")

    def _get_key(self, command: str, chat_id: Optional[int] = None) -> str:
        """
        Generate key for cooldown tracking

        Args:
            command: Command name
            chat_id: Optional chat ID for per-chat cooldowns

        Returns:
            Key string
        """
        if chat_id is None:
            return command
        return f"{command}:{chat_id}"

    def can_execute(
        self, command: str, cooldown_hours: int = 24, chat_id: Optional[int] = None
    ) -> tuple[bool, Optional[timedelta]]:
        """
        Check if command can be executed based on cooldown

        Args:
            command: Command name (e.g., 'kill_random')
            cooldown_hours: Cooldown period in hours
            chat_id: Optional chat ID for per-chat cooldowns

        Returns:
            Tuple of (can_execute: bool, remaining_time: Optional[timedelta])
        """
        now = datetime.now(self.moscow_tz)
        key = self._get_key(command, chat_id)

        if key not in self._last_used:
            return True, None

        last_used = self._last_used[key]
        time_passed = now - last_used
        cooldown = timedelta(hours=cooldown_hours)

        if time_passed >= cooldown:
            return True, None

        remaining = cooldown - time_passed
        return False, remaining

    def mark_used(self, command: str, chat_id: Optional[int] = None) -> None:
        """
        Mark command as used

        Args:
            command: Command name
            chat_id: Optional chat ID for per-chat cooldowns
        """
        now = datetime.now(self.moscow_tz)
        key = self._get_key(command, chat_id)
        self._last_used[key] = now
        logger.info(
            f"Command '{command}' used in chat {chat_id or 'global'} "
            f"at {now.strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def get_remaining_cooldown(
        self, command: str, cooldown_hours: int = 24, chat_id: Optional[int] = None
    ) -> Optional[timedelta]:
        """
        Get remaining cooldown time for a command

        Args:
            command: Command name
            cooldown_hours: Cooldown period in hours
            chat_id: Optional chat ID for per-chat cooldowns

        Returns:
            Remaining time or None if command can be executed
        """
        _, remaining = self.can_execute(command, cooldown_hours, chat_id)
        return remaining


# Global service instance
cooldown_service = CommandCooldownService()


def format_timedelta(td: timedelta) -> str:
    """
    Format timedelta to human-readable string

    Args:
        td: Time delta to format

    Returns:
        Formatted string like "23h 45m"
    """
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60

    if hours > 0:
        return f"{hours}ч {minutes}м"
    return f"{minutes}м"


async def global_command_cooldown(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """
    Check if command can be executed based on global cooldown

    Args:
        update: Telegram update
        context: Callback context

    Returns:
        True if command can proceed, False if blocked
    """
    if not update.message or not update.message.text:
        return True

    # Extract command from message
    command_text = update.message.text.split()[0].lstrip("/")
    if "@" in command_text:  # Handle /command@botname format
        command_text = command_text.split("@")[0]

    # Check cooldown (24 hours)
    can_execute, remaining = cooldown_service.can_execute(
        command_text, cooldown_hours=24
    )

    if not can_execute and remaining is not None:
        remaining_str = format_timedelta(remaining)
        user = update.effective_user
        chat_id = update.effective_chat.id if update.effective_chat else "unknown"

        logger.warning(
            f"Command '{command_text}' blocked for user {user.id} "
            f"in chat {chat_id}. Remaining cooldown: {remaining_str}"
        )

        await update.message.reply_text(f"Попробуйте снова через {remaining_str}.")
        return False

    return True
