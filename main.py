"""Main entry point for the bot"""

import sys

from telegram import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    Update,
)
from telegram.ext import Application

from bot.config import settings
from bot.handlers import register_all_handlers
from bot.utils import setup_logger


async def setup_bot_commands(app: Application) -> None:
    """Setup bot command menu"""
    commands = [
        BotCommand("start", "Начать работу с ботом"),
        BotCommand("ping", "Получить случайную фразу"),
        BotCommand("help", "Показать помощь"),
    ]

    # Set commands for private chats
    await app.bot.set_my_commands(commands, scope=BotCommandScopeAllPrivateChats())

    # Set commands for group chats
    await app.bot.set_my_commands(commands, scope=BotCommandScopeAllGroupChats())


def main() -> None:
    """Initialize and run the bot"""
    # Setup logging
    logger = setup_logger(level=settings.LOG_LEVEL)

    try:
        logger.info("Starting Telegram bot...")
        logger.info(f"Debug mode: {settings.DEBUG}")

        # Create application
        app = Application.builder().token(settings.BOT_TOKEN).build()

        # Register all handlers
        register_all_handlers(app)

        # Setup bot commands menu
        app.post_init = setup_bot_commands

        # Start polling
        logger.info("Bot is running. Press Ctrl+C to stop.")
        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,  # Ignore pending updates on restart
        )

    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Critical error occurred: {e}", exc_info=True)
        logger.info("Bot will be restarted by Docker...")
        sys.exit(1)  # Exit with error code to trigger restart


if __name__ == "__main__":
    main()
