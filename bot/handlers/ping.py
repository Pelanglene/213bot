"""Ping command handler"""

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.config import settings
from bot.middlewares import rate_limiter
from bot.services import PhraseService

logger = logging.getLogger(__name__)

# Initialize phrase service
phrase_service = PhraseService(settings.PHRASES_FILE)


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /ping command

    Args:
        update: Telegram update
        context: Callback context
    """
    user = update.effective_user

    # Check rate limit
    if not rate_limiter.is_allowed(user.id):
        remaining = rate_limiter.get_remaining_cooldown(user.id)
        await update.message.reply_text(
            f"⏳ Подожди {remaining:.1f} сек перед следующим запросом",
            reply_to_message_id=update.message.message_id,
        )
        return

    logger.info(f"User {user.id} ({user.username}) used /ping command")

    phrase = phrase_service.get_random_phrase()

    if phrase is None:
        await update.message.reply_text(
            "No phrases available",
            reply_to_message_id=update.message.message_id,
        )
        logger.warning("No phrases available for /ping command")
        return

    await update.message.reply_text(
        phrase,
        reply_to_message_id=update.message.message_id,
    )


def register_ping_handlers(app: Application) -> None:
    """
    Register ping command handlers

    Args:
        app: Telegram application instance
    """
    app.add_handler(CommandHandler("ping", ping_command))
    logger.info("Ping handlers registered")
