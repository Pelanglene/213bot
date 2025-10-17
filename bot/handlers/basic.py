"""Basic command handlers"""

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /start command

    Args:
        update: Telegram update
        context: Callback context
    """
    user = update.effective_user
    logger.info(f"User {user.id} ({user.username}) started the bot")

    await update.message.reply_text(
        "На связи бот 213.\n\n"
        "Доступные команды:\n"
        "/start - это сообщение\n"
        "/ping - пинг (макс. 1 запрос в секунду)\n"
        "/can_delete - проверить права на удаление сообщений (этот чат)\n"
        "/reel - случайный Instagram Reels\n"
        "/help - помощь"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /help command

    Args:
        update: Telegram update
        context: Callback context
    """
    await update.message.reply_text(
        "📖 Помощь:\n\n"
        "/start - начать работу с ботом\n"
        "/ping - пинг (ограничение: 1 раз в секунду)\n"
        "/can_delete - проверить, может ли бот удалять сообщения в чате\n"
        "/reel - прислать случайный Instagram Reels\n"
        "/help - показать это сообщение"
    )


def register_basic_handlers(app: Application) -> None:
    """
    Register basic command handlers

    Args:
        app: Telegram application instance
    """
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    logger.info("Basic handlers registered")
