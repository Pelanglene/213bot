"""Chat activity tracking service"""

import logging
from datetime import datetime, timedelta
from typing import Dict
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


class ChatActivityService:
    """Track chat activity and detect inactive chats"""

    def __init__(self, inactive_minutes: int = 15):
        self._last_activity: Dict[int, datetime] = {}
        self.inactive_threshold = timedelta(minutes=inactive_minutes)
        self.moscow_tz = ZoneInfo("Europe/Moscow")
        self.active_hours = (9, 21)  # 9:00 to 21:00 MSK

    def update_activity(self, chat_id: int) -> None:
        """
        Update last activity time for a chat

        Args:
            chat_id: Telegram chat ID
        """
        now = datetime.now(self.moscow_tz)
        self._last_activity[chat_id] = now
        logger.debug(
            f"Updated activity for chat_id={chat_id} at {now.strftime('%H:%M:%S')}"
        )

    def is_chat_inactive(self, chat_id: int) -> bool:
        """
        Check if chat is inactive for more than threshold

        Args:
            chat_id: Telegram chat ID

        Returns:
            True if chat is inactive and should get dead chat message
        """
        # Never sent a message in this chat
        if chat_id not in self._last_activity:
            return False

        now = datetime.now(self.moscow_tz)

        # Check if current time is within active hours
        if not self._is_active_hours(now):
            return False

        # Check if enough time has passed
        last_activity = self._last_activity[chat_id]
        time_passed = now - last_activity

        return time_passed >= self.inactive_threshold

    def mark_dead_chat_sent(self, chat_id: int) -> None:
        """
        Mark that dead chat message was sent and update last activity time

        Args:
            chat_id: Telegram chat ID
        """
        # Update last activity to current time so next message will be in 15 minutes
        now = datetime.now(self.moscow_tz)
        self._last_activity[chat_id] = now
        next_check = (now + self.inactive_threshold).strftime("%H:%M:%S")
        logger.info(
            f"Dead chat marked for chat_id={chat_id}, next check at {next_check}"
        )

    def _is_active_hours(self, dt: datetime) -> bool:
        """
        Check if time is within active hours (9:00-21:00 MSK)

        Args:
            dt: Datetime to check (should be in MSK timezone)

        Returns:
            True if within active hours
        """
        hour = dt.hour
        return self.active_hours[0] <= hour < self.active_hours[1]

    def get_inactive_chats(self) -> list[int]:
        """
        Get list of chat IDs that are inactive and need dead chat message

        Returns:
            List of chat IDs
        """
        total_chats = len(self._last_activity)
        if total_chats > 0:
            logger.debug(f"Checking {total_chats} tracked chat(s) for inactivity")

        return [
            chat_id for chat_id in self._last_activity if self.is_chat_inactive(chat_id)
        ]
