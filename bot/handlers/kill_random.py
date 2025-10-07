"""Kill random user command handler"""

import logging
import random
from datetime import datetime, timedelta

from telegram import Chat, ChatMember, ChatPermissions, Update
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.middlewares.command_cooldown import cooldown_service, format_timedelta
from bot.services.telegram_client_service import telegram_client_service

logger = logging.getLogger(__name__)


async def kill_random_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle /kill_random command - kicks a random member from the chat

    Args:
        update: Telegram update
        context: Callback context
    """
    chat = update.effective_chat
    user = update.effective_user

    # Check if this is a group chat
    if chat.type not in [Chat.GROUP, Chat.SUPERGROUP]:
        await update.message.reply_text(
            "❌ Эта команда работает только в групповых чатах",
            reply_to_message_id=update.message.message_id,
        )
        return

    # Check per-chat cooldown (1 hour)
    can_execute, remaining = cooldown_service.can_execute(
        "kill_random", cooldown_hours=1, chat_id=chat.id
    )
    if not can_execute and remaining is not None:
        remaining_str = format_timedelta(remaining)
        logger.warning(
            f"User {user.id} ({user.username}) tried to use /kill_random "
            f"in chat {chat.id} but command is on cooldown. "
            f"Remaining: {remaining_str}"
        )
        await update.message.reply_text(
            f"⏳ Команда уже использовалась в этом чате. "
            f"Попробуйте снова через {remaining_str}.",
            reply_to_message_id=update.message.message_id,
        )
        return

    logger.info(
        f"User {user.id} ({user.username}) used /kill_random command in chat {chat.id}"
    )

    try:
        # Check if bot has admin rights
        bot_member = await chat.get_member(context.bot.id)
        if bot_member.status not in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]:
            await update.message.reply_text(
                "❌ У бота нет прав администратора для кика участников",
                reply_to_message_id=update.message.message_id,
            )
            logger.warning(f"Bot doesn't have admin rights in chat {chat.id}")
            return

        if not bot_member.can_restrict_members:
            await update.message.reply_text(
                "❌ У бота нет права ограничивать участников",
                reply_to_message_id=update.message.message_id,
            )
            logger.warning(f"Bot can't restrict members in chat {chat.id}")
            return

        # Get chat administrators
        admins = await chat.get_administrators()
        admin_ids = {admin.user.id for admin in admins}

        # Get all chat members using Client API
        try:
            all_members = await telegram_client_service.get_chat_members(
                chat_id=chat.id, exclude_bots=True, exclude_deleted=True
            )
            logger.info(f"Retrieved {len(all_members)} members from chat {chat.id}")

            # Filter out admins
            potential_targets = [
                uid
                for uid in all_members
                if uid not in admin_ids and uid != context.bot.id
            ]

            logger.info(
                f"Filtered to {len(potential_targets)} potential targets "
                f"(excluded {len(admin_ids)} admins)"
            )

        except Exception as e:
            logger.error(
                f"Failed to get members using Client API for chat {chat.id}: {e}",
                exc_info=True,
            )
            await update.message.reply_text(
                "❌ Не удалось получить список участников чата. "
                "Убедитесь, что аккаунт добавлен в чат.",
                reply_to_message_id=update.message.message_id,
            )
            return

        # Check if we have enough targets
        if len(potential_targets) < 1:
            await update.message.reply_text(
                "❌ В чате недостаточно участников для рулетки "
                "(все либо администраторы, либо боты)",
                reply_to_message_id=update.message.message_id,
            )
            logger.warning(f"No potential targets found in chat {chat.id}")
            return

        # Select random target
        target_id = random.choice(potential_targets)
        target_member = await chat.get_member(target_id)

        # Mute the user for 3 hours - no permissions
        mute_until = datetime.now() + timedelta(hours=3)
        permissions = ChatPermissions(can_send_messages=False)
        await chat.restrict_member(
            user_id=target_id, permissions=permissions, until_date=mute_until
        )

        # Get target name
        target_name = target_member.user.full_name
        if target_member.user.username:
            target_name = f"@{target_member.user.username}"

        await update.message.reply_text(
            f"🎯 Рулетка выбрала жертву: {target_name}\n" f"🔇 Мут на 3 часа!",
            reply_to_message_id=update.message.message_id,
        )

        logger.info(
            f"User {target_id} ({target_name}) was muted for 3 hours in chat {chat.id} "
            f"by /kill_random command from user {user.id}"
        )

        # Mark command as used (start 1h cooldown for this chat)
        cooldown_service.mark_used("kill_random", chat_id=chat.id)

    except TelegramError as e:
        logger.error(f"Telegram error in /kill_random: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Ошибка при попытке мута: {str(e)}",
            reply_to_message_id=update.message.message_id,
        )
    except Exception as e:
        logger.error(f"Unexpected error in /kill_random: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Произошла непредвиденная ошибка",
            reply_to_message_id=update.message.message_id,
        )


def register_kill_random_handlers(app: Application) -> None:
    """
    Register kill_random command handlers

    Args:
        app: Telegram application instance
    """
    app.add_handler(CommandHandler("kill_random", kill_random_command))
    logger.info("Kill random handlers registered")
