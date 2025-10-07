"""Telegram Client API service for accessing features not available in Bot API"""

import asyncio
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

    async def _ensure_connected(self) -> bool:
        """
        Ensure client is connected, reconnect if needed

        Returns:
            True if connected successfully, False otherwise
        """
        if not self.client:
            logger.error("Client is not initialized")
            return False

        try:
            # Check if client is connected
            if not self.client.is_connected:
                logger.warning("Client disconnected, attempting to reconnect...")
                await self.client.start()
                logger.info("Client reconnected successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to ensure connection: {e}", exc_info=True)
            return False

    async def get_chat_members(
        self,
        chat_id: int,
        exclude_bots: bool = True,
        exclude_deleted: bool = True,
        max_retries: int = 3,
    ) -> List[int]:
        """
        Get all members of a chat using Client API with retry logic

        Args:
            chat_id: Chat ID to get members from
            exclude_bots: Whether to exclude bots from the list
            exclude_deleted: Whether to exclude deleted accounts
            max_retries: Maximum number of retry attempts

        Returns:
            List of user IDs

        Raises:
            ValueError: If client is not initialized
            RPCError: If Telegram API returns an error after all retries
        """
        if not self.client or not self._initialized:
            raise ValueError("Telegram Client is not initialized")

        last_error = None

        for attempt in range(max_retries):
            try:
                # Ensure client is connected before attempting
                if not await self._ensure_connected():
                    raise ConnectionError("Failed to establish connection")

                member_ids = []

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
                    f"Waiting {e.value} seconds..."
                )
                await asyncio.sleep(e.value)
                # Don't count FloodWait as a retry attempt
                continue

            except (ConnectionError, ConnectionResetError, OSError) as e:
                last_error = e
                logger.warning(
                    f"Connection error on attempt {attempt + 1}/{max_retries} "
                    f"for chat {chat_id}: {e}"
                )

                if attempt < max_retries - 1:
                    # Wait before retry with exponential backoff
                    wait_time = 2**attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)

                    # Try to reconnect
                    try:
                        if self.client.is_connected:
                            await self.client.stop()
                        await self.client.start()
                        logger.info("Reconnected successfully")
                    except Exception as reconnect_error:
                        logger.error(f"Reconnection failed: {reconnect_error}")
                else:
                    logger.error(f"Failed to get members after {max_retries} attempts")

            except RPCError as e:
                logger.error(
                    f"Telegram API error when getting members from chat {chat_id}: {e}",
                    exc_info=True,
                )
                raise

            except Exception as e:
                last_error = e
                logger.error(
                    f"Unexpected error on attempt {attempt + 1}/{max_retries} "
                    f"for chat {chat_id}: {e}",
                    exc_info=True,
                )

                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)

        # If we get here, all retries failed
        raise ConnectionError(
            f"Failed to get chat members after {max_retries} attempts. "
            f"Last error: {last_error}"
        )


# Global service instance
telegram_client_service = TelegramClientService()
