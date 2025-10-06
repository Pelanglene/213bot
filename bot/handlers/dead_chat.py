"""Dead chat detection handler"""

import logging

from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from bot.services.chat_activity_service import ChatActivityService

logger = logging.getLogger(__name__)

# Global service instance
chat_activity_service = ChatActivityService()


async def track_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Track any message in chat to update activity

    Args:
        update: Telegram update
        context: Callback context
    """
    if update.effective_chat:
        chat_id = update.effective_chat.id
        chat_activity_service.update_activity(chat_id)


async def check_inactive_chats(context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Background job to check for inactive chats and send dead chat message

    Args:
        context: Callback context
    """
    inactive_chats = chat_activity_service.get_inactive_chats()

    for chat_id in inactive_chats:
        try:
            await context.bot.send_message(chat_id=chat_id, text="💀 dead chat")
            chat_activity_service.mark_dead_chat_sent(chat_id)
            logger.info(f"Sent dead chat message to {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send dead chat message to {chat_id}: {e}")


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
        logger.info("Dead chat detection handler registered with 60s interval")
    else:
        logger.warning("Job queue not available, dead chat detection disabled")
