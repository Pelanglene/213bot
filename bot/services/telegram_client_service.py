"""Telegram Client API service for accessing features not available in Bot API"""

import logging
from typing import List, Optional

from pyrogram import Client
from pyrogram.errors import FloodWait, RPCError

from bot.config import settings

logger = logging.getLogger(__name__)


class TelegramClientService:
    """Service for interacting with Telegram Client API"""

    def __init__(self):
        self.client: Optional[Client] = None
        self._initialized = False

    async def initialize(self):
        """Initialize Pyrogram client"""
        if self._initialized:
            return

        try:
            self.client = Client(
                name=settings.SESSION_NAME,
                api_id=settings.API_ID,
                api_hash=settings.API_HASH,
                workdir="./data",
            )
            await self.client.start()
            self._initialized = True
            logger.info("Telegram Client API service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram Client: {e}", exc_info=True)
            raise

    async def close(self):
        """Close Pyrogram client"""
        if self.client and self._initialized:
            try:
                await self.client.stop()
                self._initialized = False
                logger.info("Telegram Client API service closed")
            except Exception as e:
                logger.error(f"Error closing Telegram Client: {e}", exc_info=True)

    async def get_chat_members(
        self, chat_id: int, exclude_bots: bool = True, exclude_deleted: bool = True
    ) -> List[int]:
        """
        Get all members of a chat using Client API

        Args:
            chat_id: Chat ID to get members from
            exclude_bots: Whether to exclude bots from the list
            exclude_deleted: Whether to exclude deleted accounts

        Returns:
            List of user IDs

        Raises:
            ValueError: If client is not initialized
            RPCError: If Telegram API returns an error
        """
        if not self.client or not self._initialized:
            raise ValueError("Telegram Client is not initialized")

        member_ids = []

        try:
            async for member in self.client.get_chat_members(chat_id):
                # Skip if user is None
                if not member.user:
                    continue

                # Skip bots if needed
                if exclude_bots and member.user.is_bot:
                    continue

                # Skip deleted accounts if needed
                if exclude_deleted and member.user.is_deleted:
                    continue

                member_ids.append(member.user.id)

            logger.info(
                f"Retrieved {len(member_ids)} members from chat {chat_id} "
                f"(exclude_bots={exclude_bots}, exclude_deleted={exclude_deleted})"
            )
            return member_ids

        except FloodWait as e:
            logger.warning(
                f"FloodWait error when getting members from chat {chat_id}. "
                f"Need to wait {e.value} seconds"
            )
            raise
        except RPCError as e:
            logger.error(
                f"Telegram API error when getting members from chat {chat_id}: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error when getting members from chat {chat_id}: {e}",
                exc_info=True,
            )
            raise


# Global service instance
telegram_client_service = TelegramClientService()
