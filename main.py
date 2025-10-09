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
from bot.middlewares import register_anti_bot_filter
from bot.middlewares.user_tracker import register_user_tracker
from bot.services.telegram_client_service import telegram_client_service
from bot.utils import setup_logger


# test 2
async def post_init(app: Application) -> None:
    """Post-initialization setup"""
    # Initialize Telegram Client API service
    await telegram_client_service.initialize()

    # Setup bot command menu
    commands = [
        BotCommand("start", "Начать работу с ботом"),
        BotCommand("ping", "Получить случайную фразу"),
        BotCommand("kill_random", "Кикнуть случайного участника (только группы)"),
        BotCommand("can_delete", "Проверить право удалять сообщения"),
        BotCommand("help", "Показать помощь"),
        BotCommand("goon", "NSFW waifu/neko/trap/blowjob (18+)"),
        BotCommand("top_gooners", "Топ гоунеров за месяц"),
    ]

    # Set commands for private chats
    await app.bot.set_my_commands(commands, scope=BotCommandScopeAllPrivateChats())

    # Set commands for group chats
    await app.bot.set_my_commands(commands, scope=BotCommandScopeAllGroupChats())


async def post_shutdown(app: Application) -> None:
    """Post-shutdown cleanup"""
    # Close Telegram Client API service
    await telegram_client_service.close()


def main() -> None:
    """Initialize and run the bot"""
    # Setup logging
    logger = setup_logger(level=settings.LOG_LEVEL)

    try:
        logger.info("Starting Telegram bot...")
        logger.info(f"Debug mode: {settings.DEBUG}")

        # Create application
        app = Application.builder().token(settings.BOT_TOKEN).build()

        # Register anti-bot filter BEFORE everything else
        register_anti_bot_filter(app)

        # Register user tracker middleware
        register_user_tracker(app)

        # Register all handlers
        register_all_handlers(app)

        # Setup post-init and post-shutdown hooks
        app.post_init = post_init
        app.post_shutdown = post_shutdown

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
