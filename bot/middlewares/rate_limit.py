"""Rate limiting middleware"""

import logging
from datetime import datetime, timedelta
from typing import Dict

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter to prevent spam"""

    def __init__(self, cooldown_seconds: float = 1.0):
        """
        Initialize rate limiter

        Args:
            cooldown_seconds: Minimum seconds between requests per user
        """
        self.cooldown = timedelta(seconds=cooldown_seconds)
        self.last_request: Dict[int, datetime] = {}

    def is_allowed(self, user_id: int) -> bool:
        """
        Check if user is allowed to make a request

        Args:
            user_id: Telegram user ID

        Returns:
            True if allowed, False if rate limited
        """
        now = datetime.now()

        if user_id not in self.last_request:
            self.last_request[user_id] = now
            return True

        time_since_last = now - self.last_request[user_id]

        if time_since_last < self.cooldown:
            remaining = (self.cooldown - time_since_last).total_seconds()
            logger.warning(
                f"Rate limit hit for user {user_id}. "
                f"Remaining cooldown: {remaining:.2f}s"
            )
            return False

        self.last_request[user_id] = now
        return True

    def get_remaining_cooldown(self, user_id: int) -> float:
        """
        Get remaining cooldown time for user

        Args:
            user_id: Telegram user ID

        Returns:
            Remaining seconds, 0 if no cooldown
        """
        if user_id not in self.last_request:
            return 0.0

        now = datetime.now()
        time_since_last = now - self.last_request[user_id]

        if time_since_last < self.cooldown:
            return (self.cooldown - time_since_last).total_seconds()

        return 0.0

    def reset_user(self, user_id: int) -> None:
        """
        Reset rate limit for specific user

        Args:
            user_id: Telegram user ID
        """
        if user_id in self.last_request:
            del self.last_request[user_id]
            logger.info(f"Rate limit reset for user {user_id}")


# Global rate limiter instance
rate_limiter = RateLimiter(cooldown_seconds=1.0)
