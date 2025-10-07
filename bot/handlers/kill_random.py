"""Kill random user command handler"""

import logging
import random

from telegram import Chat, ChatMember, Update
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.middlewares.command_cooldown import cooldown_service, format_timedelta

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

    # Check if user is admin (admins can bypass cooldown)
    try:
        user_member = await chat.get_member(user.id)
        is_admin = user_member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except Exception as e:
        logger.warning(f"Could not check admin status for user {user.id}: {e}")
        is_admin = False

    # Check global cooldown (24 hours) - skip for admins
    if not is_admin:
        can_execute, remaining = cooldown_service.can_execute(
            "kill_random", cooldown_hours=24
        )
        if not can_execute and remaining is not None:
            remaining_str = format_timedelta(remaining)
            logger.warning(
                f"User {user.id} ({user.username}) tried to use /kill_random "
                f"in chat {chat.id} but command is on cooldown. "
                f"Remaining: {remaining_str}"
            )
            await update.message.reply_text(
                f"⏳ Эта команда уже использовалась сегодня.\n"
                f"Попробуйте снова через {remaining_str}.",
                reply_to_message_id=update.message.message_id,
            )
            return

    logger.info(
        f"User {user.id} ({user.username}) used /kill_random command in chat {chat.id}"
        + (" [ADMIN]" if is_admin else "")
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

        # Get chat members count
        members_count = await chat.get_member_count()

        # If too few members, don't proceed
        if members_count <= 2:  # Bot + at least 1 other user
            await update.message.reply_text(
                "❌ В чате недостаточно участников для рулетки",
                reply_to_message_id=update.message.message_id,
            )
            return

        # Get chat administrators
        admins = await chat.get_administrators()
        admin_ids = {admin.user.id for admin in admins}

        # Collect recent message senders as potential targets
        # This is a workaround since we can't easily get all members
        # We'll use a fallback: try to get members from recent messages
        potential_targets = []

        # Try to get members from chat history
        # Note: This won't work for all chats, but it's the best we can do
        # without storing member information
        if context.chat_data and "recent_users" in context.chat_data:
            potential_targets = [
                uid
                for uid in context.chat_data["recent_users"]
                if uid not in admin_ids and uid != context.bot.id
            ]

        # If we don't have any recent users, we need to notify
        if not potential_targets:
            await update.message.reply_text(
                "⚠️ Не могу найти участников для кика. "
                "Бот еще не накопил информацию об активных участниках чата.",
                reply_to_message_id=update.message.message_id,
            )
            logger.warning(f"No potential targets found in chat {chat.id}")
            return

        # Select random target
        target_id = random.choice(potential_targets)
        target_member = await chat.get_member(target_id)

        # Kick the user
        await chat.ban_member(target_id)
        # Immediately unban to allow them to rejoin
        await chat.unban_member(target_id)

        # Get target name
        target_name = target_member.user.full_name
        if target_member.user.username:
            target_name = f"@{target_member.user.username}"

        await update.message.reply_text(
            f"🎯 Рулетка выбрала жертву: {target_name}\n" f"👋 Пока-пока!",
            reply_to_message_id=update.message.message_id,
        )

        logger.info(
            f"User {target_id} ({target_name}) was kicked from chat {chat.id} "
            f"by /kill_random command from user {user.id}"
        )

        # Mark command as used (start 24h cooldown)
        cooldown_service.mark_used("kill_random")

    except TelegramError as e:
        logger.error(f"Telegram error in /kill_random: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Ошибка при попытке кика: {str(e)}",
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
