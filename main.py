"""Main entry point for the bot"""

import sys

from telegram import Update
from telegram.ext import Application

from bot.config import settings
from bot.handlers import register_all_handlers
from bot.utils import setup_logger


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
