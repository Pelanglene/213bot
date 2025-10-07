"""Bot configuration settings"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings"""

    def __init__(self):
        self.BOT_TOKEN: str = self._get_required_env("BOT_TOKEN")
        self.API_ID: int = int(self._get_required_env("API_ID"))
        self.API_HASH: str = self._get_required_env("API_HASH")
        self.SESSION_NAME: str = os.getenv("SESSION_NAME", "bot_session")
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
        self.PHRASES_FILE: Path = Path(os.getenv("PHRASES_FILE", "data/phrases.json"))
        self.DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
        self.DEAD_CHAT_MINUTES: int = int(os.getenv("DEAD_CHAT_MINUTES", "15"))

    @staticmethod
    def _get_required_env(key: str) -> str:
        """Get required environment variable or raise error"""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Environment variable {key} is required")
        return value


settings = Settings()
