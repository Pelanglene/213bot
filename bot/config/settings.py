"""Bot configuration settings"""

import os
from pathlib import Path
import logging

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


class Settings:
    """Application settings"""

    def __init__(self):
        self.BOT_TOKEN: str = self._get_required_env("BOT_TOKEN")
        # Optional credentials for Telegram Client API (Pyrogram)
        api_id_str = os.getenv("API_ID")
        self.API_ID = int(api_id_str) if api_id_str else None  # type: ignore[assignment]
        self.API_HASH = os.getenv("API_HASH")
        self.SESSION_NAME: str = os.getenv("SESSION_NAME", "bot_session")
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
        self.PHRASES_FILE: Path = Path(os.getenv("PHRASES_FILE", "data/phrases.json"))
        self.STORAGE_PATH: Path = Path(os.getenv("STORAGE_PATH", "storage/"))
        self.DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
        self.TEST_MODE: bool = os.getenv("TEST_MODE", "false").lower() == "true"
        self.DEAD_CHAT_MINUTES: int = int(os.getenv("DEAD_CHAT_MINUTES", "15"))
        self.KILL_RANDOM_MUTE_HOURS: int = int(os.getenv("KILL_RANDOM_MUTE_HOURS", "1"))

        if self.TEST_MODE:
            logger.info("TEST_MODE is enabled")

    @staticmethod
    def _get_required_env(key: str) -> str:
        """Get required environment variable or raise error"""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Environment variable {key} is required")
        return value


settings = Settings()
