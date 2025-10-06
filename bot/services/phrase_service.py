"""Service for managing phrases"""

import json
import logging
import random
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class PhraseService:
    """Service for loading and managing phrases"""

    def __init__(self, phrases_file: Path):
        """
        Initialize phrase service

        Args:
            phrases_file: Path to JSON file with phrases
        """
        self.phrases_file = phrases_file
        self._phrases: List[str] = []
        self.load_phrases()

    def load_phrases(self) -> None:
        """Load phrases from JSON file"""
        try:
            with open(self.phrases_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._phrases = data.get("phrases", [])
                logger.info(
                    f"Loaded {len(self._phrases)} phrases from {self.phrases_file}"
                )
        except FileNotFoundError:
            logger.error(f"Phrases file {self.phrases_file} not found")
            self._phrases = ["Pong!"]
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {self.phrases_file}: {e}")
            self._phrases = ["Pong!"]
        except Exception as e:
            logger.error(f"Error loading phrases: {e}")
            self._phrases = ["Pong!"]

    def get_random_phrase(self) -> Optional[str]:
        """
        Get random phrase from loaded phrases

        Returns:
            Random phrase or None if no phrases available
        """
        if not self._phrases:
            return None
        return random.choice(self._phrases)

    def get_all_phrases(self) -> List[str]:
        """
        Get all loaded phrases

        Returns:
            List of all phrases
        """
        return self._phrases.copy()

    def reload_phrases(self) -> None:
        """Reload phrases from file"""
        self.load_phrases()
