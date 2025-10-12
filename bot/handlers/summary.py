"""Chat summarization handler

Tracks messages for daily summaries and schedules a job at 22:00 MSK to
summarize each chat's messages for the day using a local LLM.

Provides a test-only command /summary when TEST_MODE is enabled.
"""

from __future__ import annotations

import logging
from datetime import datetime, time
from typing import List
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)

from bot.config import settings
from bot.services.message_log_service import message_log_service
from bot.services.summarization_service import summarization_service


logger = logging.getLogger(__name__)


async def track_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Record text messages for daily summarization (ignore bots and service msgs)."""
    try:
        if not update.effective_chat or not update.effective_user:
            return
        if update.effective_user.is_bot:
            return
        msg = update.effective_message
        if not msg or not msg.text:
            return
        # Ignore commands to avoid polluting logs with bot commands
        if msg.text.startswith("/"):
            return
        message_log_service.record_message(
            chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            sender_id=update.effective_user.id,
            text=msg.text,
            sent_at=msg.date if getattr(msg, "date", None) else None,
        )
    except Exception as e:
        logger.debug(f"Failed to record message for summarization: {e}")


def _date_key_now_msk() -> str:
    now_msk = datetime.now(ZoneInfo("Europe/Moscow"))
    return now_msk.date().isoformat()


def _build_summary_input_text(lines: List[str], max_chars: int = 28000) -> str:
    # Basic concatenation with trimming to avoid excessively long inputs
    joined = "\n".join(lines)
    if len(joined) > max_chars:
        return joined[-max_chars:]
    return joined


async def run_daily_summaries(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send a summary for each chat at 22:00 MSK."""
    date_key = _date_key_now_msk()
    chat_ids = message_log_service.get_chats_for_date(date_key)
    if not chat_ids:
        logger.info("No chats to summarize today")
        return

    for chat_id in chat_ids:
        try:
            messages = message_log_service.get_messages_for_date(date_key, chat_id)
            if not messages:
                continue
            # Build input
            lines: List[str] = []
            for m in messages:
                # Minimal sender prefix; usernames are not stored to avoid PII
                hhmm = m.sent_at.strftime("%H:%M")
                lines.append(f"[{hhmm}] {m.text}")
            input_text = _build_summary_input_text(lines)

            summary = summarization_service.summarize_text(input_text)
            if not summary:
                summary = "(no summary)"

            await context.bot.send_message(
                chat_id=chat_id,
                text=f"📝 Сводка за сегодня (MSK):\n\n{summary}",
            )
        except Exception as e:
            logger.error(f"Failed to send daily summary to chat_id={chat_id}: {e}")
        finally:
            # Clear messages for that chat for the day after sending summary
            try:
                message_log_service.clear_date_for_chat(date_key, chat_id)
            except Exception:
                pass


async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Test-only command to run today's summary immediately for the current chat."""
    if not settings.TEST_MODE:
        return
    if not update.effective_chat:
        return
    chat_id = update.effective_chat.id
    date_key = _date_key_now_msk()
    try:
        messages = message_log_service.get_messages_for_date(date_key, chat_id)
        if not messages:
            await update.effective_message.reply_text("Нет данных для сводки за сегодня.")
            return
        lines = [f"[{m.sent_at.strftime('%H:%M')}] {m.text}" for m in messages]
        input_text = _build_summary_input_text(lines)
        print("Summarizing text...")
        summary = summarization_service.summarize_text(input_text)
        print("Summary:", summary)
        if not summary:
            summary = "(no summary)"
        await update.effective_message.reply_text(
            f"📝 Сводка за сегодня (MSK):\n\n{summary}"
        )
    except Exception as e:
        logger.error(f"/summary failed: {e}")
        await update.effective_message.reply_text("Ошибка при генерации сводки.")


def register_summary_handlers(app: Application) -> None:
    """Register message tracking and scheduling for daily summaries."""
    # Track only text messages from humans
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, track_text_message), group=2)

    # Schedule daily summary at 22:00 MSK
    job_queue = app.job_queue
    if job_queue:
        msk_tz = ZoneInfo("Europe/Moscow")
        job_queue.run_daily(
            run_daily_summaries,
            time=time(22, 0, tzinfo=msk_tz),
        )
        if settings.TEST_MODE:
            app.add_handler(CommandHandler("summary", summary_command))
        logger.info("Summary handlers registered (daily at 22:00 MSK)")
    else:
        logger.warning("Job queue not available, daily summaries disabled")


