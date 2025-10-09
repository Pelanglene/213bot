"""Daily vote tracking service for 'тян дня'"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from bot.config import settings

logger = logging.getLogger(__name__)


@dataclass
class DailyPhotoEntry:
    chat_id: int
    message_id: int
    file_id: str
    sent_at: datetime  # Should be in MSK tz


class DailyVoteService:
    """Track dead chat photo messages per day to select a daily winner."""

    def __init__(self, storage_dir: Optional[Path] = None):
        # Mapping: date_key (YYYY-MM-DD in MSK) -> chat_id -> list of entries
        self._entries_by_date: Dict[str, Dict[int, List[DailyPhotoEntry]]] = {}
        self.moscow_tz = ZoneInfo("Europe/Moscow")
        self.storage_dir = storage_dir
        if self.storage_dir:
            try:
                self.storage_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(
                    "Failed to create storage directory %s: %s",
                    self.storage_dir,
                    e,
                )
                self.storage_dir = None

    def _date_key(self, dt: datetime) -> str:
        dt_msk = dt.astimezone(self.moscow_tz)
        return dt_msk.date().isoformat()

    def record_entry(
        self, chat_id: int, message_id: int, file_id: str, sent_at: datetime
    ) -> None:
        """Record a photo message sent by the bot for daily voting."""
        date_key = self._date_key(sent_at)
        # Ensure date is loaded from disk first
        self._maybe_load_date(date_key)
        if date_key not in self._entries_by_date:
            self._entries_by_date[date_key] = {}
        if chat_id not in self._entries_by_date[date_key]:
            self._entries_by_date[date_key][chat_id] = []

        entry = DailyPhotoEntry(
            chat_id=chat_id,
            message_id=message_id,
            file_id=file_id,
            sent_at=sent_at.astimezone(self.moscow_tz),
        )
        self._entries_by_date[date_key][chat_id].append(entry)
        logger.debug(
            "Recorded daily vote entry: date=%s, chat_id=%s, message_id=%s",
            date_key,
            chat_id,
            message_id,
        )
        self._save_date(date_key)

    def get_chats_for_date(self, date_key: str) -> List[int]:
        """Return chat IDs that have entries for the given date key."""
        self._maybe_load_date(date_key)
        if date_key not in self._entries_by_date:
            return []
        return list(self._entries_by_date[date_key].keys())

    def get_entries_for_date(
        self, date_key: str, chat_id: int
    ) -> List[DailyPhotoEntry]:
        """Return entries for a chat on a given date key."""
        self._maybe_load_date(date_key)
        if date_key not in self._entries_by_date:
            return []
        return list(self._entries_by_date[date_key].get(chat_id, []))

    def clear_date(self, date_key: str) -> None:
        """Clear all entries for a given date key."""
        if date_key in self._entries_by_date:
            del self._entries_by_date[date_key]
            logger.info(f"Cleared daily vote entries for date {date_key}")
        # Remove persisted file
        if self.storage_dir:
            try:
                file_path = self.storage_dir / f"daily_vote_{date_key}.json"
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                logger.warning(
                    "Failed to remove storage file for %s: %s",
                    date_key,
                    e,
                )

    def prune_older_than(self, max_days: int = 7) -> None:
        """Optional: prune data older than max_days, if needed in future."""
        # Currently not implemented, as in-memory footprint is small for daily data
        pass

    def _file_path(self, date_key: str) -> Optional[Path]:
        if not self.storage_dir:
            return None
        return self.storage_dir / f"daily_vote_{date_key}.json"

    def _maybe_load_date(self, date_key: str) -> None:
        """Load entries for a date from disk if present and not yet loaded."""
        if date_key in self._entries_by_date:
            return
        file_path = self._file_path(date_key)
        if not file_path or not file_path.exists():
            return
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            result: Dict[int, List[DailyPhotoEntry]] = {}
            for chat_id_str, entries in data.items():
                chat_id = int(chat_id_str)
                result[chat_id] = []
                for e in entries:
                    try:
                        sent_at = datetime.fromisoformat(e.get("sent_at"))
                    except Exception:
                        sent_at = datetime.now(self.moscow_tz)
                    result[chat_id].append(
                        DailyPhotoEntry(
                            chat_id=chat_id,
                            message_id=int(e.get("message_id")),
                            file_id=str(e.get("file_id")),
                            sent_at=sent_at.astimezone(self.moscow_tz),
                        )
                    )
            self._entries_by_date[date_key] = result
            logger.info(f"Loaded daily vote entries from {file_path}")
        except Exception as e:
            logger.error(
                "Failed to load daily vote entries from %s: %s",
                file_path,
                e,
            )

    def _save_date(self, date_key: str) -> None:
        """Persist entries for a date to disk as JSON."""
        file_path = self._file_path(date_key)
        if not file_path:
            return
        try:
            to_dump: Dict[str, List[dict]] = {}
            for chat_id, entries in self._entries_by_date.get(date_key, {}).items():
                to_dump[str(chat_id)] = [
                    {
                        "chat_id": entry.chat_id,
                        "message_id": entry.message_id,
                        "file_id": entry.file_id,
                        "sent_at": entry.sent_at.isoformat(),
                    }
                    for entry in entries
                ]
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(to_dump, f, ensure_ascii=False, indent=2)
            logger.debug("Saved daily vote entries to %s", file_path)
        except Exception as e:
            logger.error(
                "Failed to save daily vote entries to %s: %s",
                file_path,
                e,
            )


daily_vote_service = DailyVoteService(storage_dir=settings.STORAGE_PATH)
