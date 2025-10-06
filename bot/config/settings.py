"""Bot configuration settings"""

import os
from pathlib import Path


class Settings:
    """Application settings"""

    def __init__(self):
        self.BOT_TOKEN: str = self._get_required_env("BOT_TOKEN")
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
        self.PHRASES_FILE: Path = Path(os.getenv("PHRASES_FILE", "data/phrases.json"))
        self.DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

    @staticmethod
    def _get_required_env(key: str) -> str:
        """Get required environment variable or raise error"""
        value = os.getenv(key)
        if not value:
            raise ValueError(f"Environment variable {key} is required")
        return value


settings = Settings()
