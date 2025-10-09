"""Monthly goon usage statistics service"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GoonUsage:
    user_id: int
    count: int


class GoonStatsService:
    """Track per-month goon command usage counts per chat and persist to disk."""

    def __init__(self, storage_dir: Optional[Path] = None):
        # Mapping: month_key (YYYY-MM in MSK) -> chat_id -> user_id -> count
        self._counts_by_month: Dict[str, Dict[int, Dict[int, int]]] = {}
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

    def _month_key(self, dt: datetime) -> str:
        dt_msk = dt.astimezone(self.moscow_tz)
        return dt_msk.strftime("%Y-%m")

    def _file_path(self, month_key: str) -> Optional[Path]:
        if not self.storage_dir:
            return None
        return self.storage_dir / f"goon_stats_{month_key}.json"

    def _maybe_load_month(self, month_key: str) -> None:
        if month_key in self._counts_by_month:
            return
        file_path = self._file_path(month_key)
        if not file_path or not file_path.exists():
            return
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            # data schema: { chat_id_str: { user_id_str: count } }
            loaded: Dict[int, Dict[int, int]] = {}
            for chat_id_str, per_user in data.items():
                chat_id = int(chat_id_str)
                loaded[chat_id] = {int(uid): int(cnt) for uid, cnt in per_user.items()}
            self._counts_by_month[month_key] = loaded
            logger.info(f"Loaded goon stats for {month_key} from {file_path}")
        except Exception as e:
            logger.error(f"Failed to load goon stats from {file_path}: {e}")

    def _save_month(self, month_key: str) -> None:
        file_path = self._file_path(month_key)
        if not file_path:
            return
        try:
            to_dump: Dict[str, Dict[str, int]] = {}
            for chat_id, per_user in self._counts_by_month.get(month_key, {}).items():
                to_dump[str(chat_id)] = {
                    str(uid): int(cnt) for uid, cnt in per_user.items()
                }
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(to_dump, f, ensure_ascii=False, indent=2)
            logger.debug(f"Saved goon stats for {month_key} to {file_path}")
        except Exception as e:
            logger.error(
                f"Failed to save goon stats for {month_key} to {file_path}: {e}"
            )

    def record_usage(
        self, chat_id: int, user_id: int, when: Optional[datetime] = None
    ) -> None:
        dt = when or datetime.now(self.moscow_tz)
        month_key = self._month_key(dt)
        self._maybe_load_month(month_key)

        if month_key not in self._counts_by_month:
            self._counts_by_month[month_key] = {}
        if chat_id not in self._counts_by_month[month_key]:
            self._counts_by_month[month_key][chat_id] = {}

        per_user = self._counts_by_month[month_key][chat_id]
        per_user[user_id] = per_user.get(user_id, 0) + 1
        logger.debug(
            f"Recorded goon usage: month={month_key}, chat_id={chat_id}, user_id={user_id}, count={per_user[user_id]}"
        )
        self._save_month(month_key)

    def get_top_for_month(
        self, month_key: str, chat_id: int, top_n: int = 10
    ) -> List[GoonUsage]:
        self._maybe_load_month(month_key)
        per_chat = self._counts_by_month.get(month_key, {}).get(chat_id, {})
        # Sort by count desc, then by user_id asc for stable order
        sorted_items: List[Tuple[int, int]] = sorted(
            per_chat.items(), key=lambda kv: (-kv[1], kv[0])
        )
        return [GoonUsage(user_id=uid, count=cnt) for uid, cnt in sorted_items[:top_n]]

    def clear_month(self, month_key: str) -> None:
        if month_key in self._counts_by_month:
            del self._counts_by_month[month_key]
        file_path = self._file_path(month_key)
        if file_path and file_path.exists():
            try:
                file_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to remove goon stats file {file_path}: {e}")


# Global service instance (storage_dir is provided by settings in import site)
from bot.config import settings  # late import  # noqa: E402

goon_stats_service = GoonStatsService(storage_dir=settings.STORAGE_PATH)
