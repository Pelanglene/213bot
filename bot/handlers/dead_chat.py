"""Dead chat detection handler"""

import logging
from datetime import datetime, time

from typing import Optional

import aiohttp
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, CommandHandler, filters

from bot.config import settings
from bot.services.chat_activity_service import ChatActivityService
from bot.services.daily_vote_service import daily_vote_service
from bot.services.telegram_client_service import telegram_client_service
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Global service instance
chat_activity_service = ChatActivityService(inactive_minutes=settings.DEAD_CHAT_MINUTES)


async def _fetch_neko_image_url() -> Optional[str]:
    """Fetch random neko image URL from waifu.pics API.

    Returns:
        Image URL string if successful, otherwise None.
    """
    api_url = "https://api.waifu.pics/sfw/neko"
    timeout = aiohttp.ClientTimeout(total=5)

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(api_url) as resp:
                if resp.status != 200:
                    logger.warning(
                        f"Failed to fetch neko image: status={resp.status}"
                    )
                    return None
                data = await resp.json()
                url = data.get("url")
                if isinstance(url, str) and url.startswith("http"):
                    return url
                logger.warning("Invalid response structure from waifu.pics API")
                return None
    except Exception as e:
        logger.error(f"Error fetching neko image: {e}")
        return None


async def track_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Track any message in chat to update activity (except bot's own messages)

    Args:
        update: Telegram update
        context: Callback context
    """
    if update.effective_chat and update.effective_user:
        # Ignore messages from the bot itself
        if update.effective_user.is_bot:
            return
        chat_id = update.effective_chat.id
        chat_title = update.effective_chat.title or "Private"
        chat_activity_service.update_activity(chat_id)
        logger.debug(f"Activity tracked for chat_id={chat_id} ({chat_title})")


async def check_inactive_chats(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Background job to check for inactive chats and send dead chat message

    Args:
        context: Callback context
    """
    inactive_chats = chat_activity_service.get_inactive_chats()

    if inactive_chats:
        logger.info(f"Found {len(inactive_chats)} inactive chat(s): {inactive_chats}")

    for chat_id in inactive_chats:
        try:
            photo_sent = False

            for attempt in range(5):
                image_url = await _fetch_neko_image_url()
                if not image_url:
                    logger.warning(
                        f"Attempt {attempt + 1}/5: Failed to fetch neko image URL for chat_id={chat_id}"
                    )
                    continue
                try:
                    msg = await context.bot.send_photo(
                        chat_id=chat_id, photo=image_url, caption="💀 dead chat"
                    )
                    chat_activity_service.mark_dead_chat_sent(chat_id)
                    # Record for daily voting if file_id is available
                    try:
                        file_id = msg.photo[-1].file_id if getattr(msg, "photo", None) else None
                        if file_id:
                            sent_at = getattr(msg, "date", datetime.now(ZoneInfo("UTC")))
                            daily_vote_service.record_entry(
                                chat_id=chat_id,
                                message_id=msg.message_id,
                                file_id=file_id,
                                sent_at=sent_at,
                            )
                    except Exception as rec_err:
                        logger.warning(
                            f"Failed to record daily vote entry for chat_id={chat_id}: {rec_err}"
                        )
                    logger.info(
                        f"Sent dead chat photo to chat_id={chat_id} on attempt {attempt + 1}"
                    )
                    photo_sent = True
                    break
                except Exception as send_photo_err:
                    logger.warning(
                        f"Attempt {attempt + 1}/5: Failed to send photo for chat_id={chat_id}: {send_photo_err}"
                    )

            if photo_sent:
                continue

            await context.bot.send_message(chat_id=chat_id, text="💀 dead chat")
            chat_activity_service.mark_dead_chat_sent(chat_id)
            logger.info(f"Sent dead chat message (fallback text) to chat_id={chat_id}")
        except Exception as e:
            logger.error(f"Failed to send dead chat message to chat_id={chat_id}: {e}")


async def _announce_tyan_for_date(context: ContextTypes.DEFAULT_TYPE, date_key: str) -> None:
    """Core logic to announce winners for a given MSK date key across chats."""
    chat_ids = daily_vote_service.get_chats_for_date(date_key)
    if not chat_ids:
        logger.info("No daily vote entries to process today")
        return

    for chat_id in chat_ids:
        try:
            entries = daily_vote_service.get_entries_for_date(date_key, chat_id)
            if not entries:
                continue

            best_entry = None
            best_count = -1

            for entry in entries:
                count = await telegram_client_service.get_message_reaction_total(
                    chat_id=entry.chat_id, message_id=entry.message_id
                )
                logger.info(f"Entry: {entry}")
                logger.info(f"Reactions for message_id={entry.message_id} in chat_id={entry.chat_id}: {count}")

                if (
                    count > best_count
                    or (
                        count == best_count
                        and best_entry is not None
                        and entry.sent_at < best_entry.sent_at
                    )
                ):
                    best_entry = entry
                    best_count = count

            if best_entry is None:
                continue

            caption = f"👑 Тян дня! ({best_count} реакций)"
            await context.bot.send_photo(chat_id=chat_id, photo=best_entry.file_id, caption=caption)
            logger.info(
                f"Announced 'тян дня' in chat_id={chat_id}: message_id={best_entry.message_id}, reactions={best_count}"
            )
        except Exception as exc:
            logger.error(f"Failed to announce 'тян дня' for chat_id={chat_id}: {exc}")


async def announce_tyan_of_the_day(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Announce daily winner image per chat at 22:00 MSK based on reactions."""
    now_msk = datetime.now(ZoneInfo("Europe/Moscow"))
    date_key = now_msk.date().isoformat()
    await _announce_tyan_for_date(context, date_key)

    # Clear today's entries after announcement
    try:
        daily_vote_service.clear_date(date_key)
    except Exception as clear_err:
        logger.warning(f"Failed to clear daily entries for {date_key}: {clear_err}")


async def announce_tyan_of_the_day_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Test-only command to announce today's winners immediately."""
    if not settings.TEST_MODE:
        return
    now_msk = datetime.now(ZoneInfo("Europe/Moscow"))
    date_key = now_msk.date().isoformat()
    await _announce_tyan_for_date(context, date_key)
    try:
        daily_vote_service.clear_date(date_key)
    except Exception:
        pass
    if update.effective_message:
        await update.effective_message.reply_text("Готово: объявил 'тян дня' за сегодня.")


def register_dead_chat_handlers(app: Application) -> None:
    """
    Register dead chat detection handlers

    Args:
        app: Telegram application instance
    """
    # Track all messages to update activity
    app.add_handler(MessageHandler(filters.ALL, track_message), group=1)

    # Schedule background job to check inactive chats every minute
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(
            check_inactive_chats,
            interval=60,  # Check every 60 seconds
            first=60,  # Start after 60 seconds
        )
        # Schedule daily 'тян дня' announcement at 22:00 MSK
        msk_tz = ZoneInfo("Europe/Moscow")
        job_queue.run_daily(
            announce_tyan_of_the_day,
            time=time(22, 0, tzinfo=msk_tz),
        )
        # Register test-only command when TEST_MODE is enabled
        if settings.TEST_MODE:
            app.add_handler(CommandHandler("announce_tyan_of_the_day", announce_tyan_of_the_day_command))
        logger.info(
            f"Dead chat detection handler registered with 60s check interval, "
            f"{settings.DEAD_CHAT_MINUTES}min inactivity threshold"
        )
    else:
        logger.warning("Job queue not available, dead chat detection disabled")
