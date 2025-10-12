"""Per-day chat message logging service with disk persistence.

Stores text messages per chat keyed by MSK date. Designed to support
daily summarization jobs.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo


logger = logging.getLogger(__name__)


@dataclass
class LoggedMessage:
    chat_id: int
    message_id: int
    sender_id: int
    text: str
    sent_at: datetime  # Stored in MSK tz


class MessageLogService:
    """Log and retrieve chat messages per date (in MSK)."""

    def __init__(self, storage_dir: Optional[Path] = None):
        # Mapping: date_key (YYYY-MM-DD in MSK) -> chat_id -> list[LoggedMessage]
        self._messages_by_date: Dict[str, Dict[int, List[LoggedMessage]]] = {}
        self.moscow_tz = ZoneInfo("Europe/Moscow")
        self.storage_dir = storage_dir
        if self.storage_dir:
            try:
                self.storage_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(
                    f"Failed to create storage directory {self.storage_dir}: {e}"
                )
                self.storage_dir = None

    def _date_key(self, dt: datetime) -> str:
        dt_msk = dt.astimezone(self.moscow_tz)
        return dt_msk.date().isoformat()

    def _file_path(self, date_key: str) -> Optional[Path]:
        if not self.storage_dir:
            return None
        return self.storage_dir / f"chat_messages_{date_key}.json"

    def _maybe_load_date(self, date_key: str) -> None:
        if date_key in self._messages_by_date:
            return
        file_path = self._file_path(date_key)
        if not file_path or not file_path.exists():
            return
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            result: Dict[int, List[LoggedMessage]] = {}
            for chat_id_str, entries in data.items():
                chat_id = int(chat_id_str)
                result[chat_id] = []
                for e in entries:
                    try:
                        sent_at = datetime.fromisoformat(e.get("sent_at"))
                    except Exception:
                        sent_at = datetime.now(self.moscow_tz)
                    msg = LoggedMessage(
                        chat_id=chat_id,
                        message_id=int(e.get("message_id", 0)),
                        sender_id=int(e.get("sender_id", 0)),
                        text=str(e.get("text", "")),
                        sent_at=sent_at.astimezone(self.moscow_tz),
                    )
                    result[chat_id].append(msg)
            self._messages_by_date[date_key] = result
            logger.info(f"Loaded message logs from {file_path}")
        except Exception as e:
            logger.error(f"Failed to load message logs from {file_path}: {e}")

    def _save_date(self, date_key: str) -> None:
        file_path = self._file_path(date_key)
        if not file_path:
            return
        try:
            to_dump: Dict[str, List[dict]] = {}
            for chat_id, messages in self._messages_by_date.get(date_key, {}).items():
                to_dump[str(chat_id)] = [
                    {
                        "chat_id": m.chat_id,
                        "message_id": m.message_id,
                        "sender_id": m.sender_id,
                        "text": m.text,
                        "sent_at": m.sent_at.isoformat(),
                    }
                    for m in messages
                ]
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(to_dump, f, ensure_ascii=False, indent=2)
            logger.debug(f"Saved message logs to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save message logs to {file_path}: {e}")

    def record_message(
        self,
        chat_id: int,
        message_id: int,
        sender_id: int,
        text: Optional[str],
        sent_at: Optional[datetime] = None,
    ) -> None:
        """Record a text-bearing message for the current MSK day.

        Empty or whitespace-only texts are ignored.
        """
        if not text:
            return
        normalized = text.strip()
        if not normalized:
            return

        dt = (sent_at or datetime.now(ZoneInfo("UTC"))).astimezone(self.moscow_tz)
        date_key = self._date_key(dt)
        self._maybe_load_date(date_key)

        if date_key not in self._messages_by_date:
            self._messages_by_date[date_key] = {}
        if chat_id not in self._messages_by_date[date_key]:
            self._messages_by_date[date_key][chat_id] = []

        self._messages_by_date[date_key][chat_id].append(
            LoggedMessage(
                chat_id=chat_id,
                message_id=message_id,
                sender_id=sender_id,
                text=normalized,
                sent_at=dt,
            )
        )
        logger.debug(
            f"Recorded message for date={date_key} chat_id={chat_id} message_id={message_id}"
        )
        self._save_date(date_key)

    def get_chats_for_date(self, date_key: str) -> List[int]:
        self._maybe_load_date(date_key)
        if date_key not in self._messages_by_date:
            return []
        return list(self._messages_by_date[date_key].keys())

    def get_messages_for_date(self, date_key: str, chat_id: int) -> List[LoggedMessage]:
        self._maybe_load_date(date_key)
        if date_key not in self._messages_by_date:
            return []
        return list(self._messages_by_date[date_key].get(chat_id, []))

    def clear_date(self, date_key: str) -> None:
        if date_key in self._messages_by_date:
            del self._messages_by_date[date_key]
        file_path = self._file_path(date_key)
        if file_path and file_path.exists():
            try:
                file_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to remove message log file {file_path}: {e}")

    def clear_date_for_chat(self, date_key: str, chat_id: int) -> None:
        self._maybe_load_date(date_key)
        if date_key in self._messages_by_date:
            by_chat = self._messages_by_date[date_key]
            if chat_id in by_chat:
                del by_chat[chat_id]
                # If now empty, also remove the file & in-memory key
                if not by_chat:
                    del self._messages_by_date[date_key]
        # Save pruned state to disk
        self._save_date(date_key)


# Global service instance (storage_dir is provided by settings in import site)
from bot.config import settings  # noqa: E402

message_log_service = MessageLogService(storage_dir=settings.STORAGE_PATH)


