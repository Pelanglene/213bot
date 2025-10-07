"""Kill random user command handler"""

import logging
import random
from datetime import datetime, timedelta

from telegram import Chat, ChatMember, ChatPermissions, Update
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

    # Check global cooldown (1 hour)
    can_execute, remaining = cooldown_service.can_execute(
        "kill_random", cooldown_hours=1
    )
    if not can_execute and remaining is not None:
        remaining_str = format_timedelta(remaining)
        logger.warning(
            f"User {user.id} ({user.username}) tried to use /kill_random "
            f"in chat {chat.id} but command is on cooldown. "
            f"Remaining: {remaining_str}"
        )
        await update.message.reply_text(
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

        potential_targets = []

        # Try to get chat members (works only for small groups <200 members)
        try:
            members_count = await chat.get_member_count()
            logger.info(f"Chat {chat.id} has {members_count} members")

            # For small groups, try to get member list through admins
            # Note: Telegram Bot API doesn't provide direct method to get all members
            # This is a limitation of the API for privacy reasons
            if members_count <= 200:
                logger.info(f"Attempting to get members from small group {chat.id}")
                # Unfortunately, there's no direct API method to get all members
                # We can only track them through messages
        except Exception as e:
            logger.debug(f"Could not get member count for chat {chat.id}: {e}")

        # Fallback: use recent users from message tracking
        if context.chat_data and "recent_users" in context.chat_data:
            potential_targets = [
                uid
                for uid in context.chat_data["recent_users"]
                if uid not in admin_ids and uid != context.bot.id
            ]
            logger.info(
                f"Using {len(potential_targets)} recent users from message tracking"
            )

        # If we still don't have any users, notify
        if not potential_targets:
            await update.message.reply_text(
                "⚠️ Не могу найти участников для мута. "
                "Бот еще не накопил информацию об активных участниках чата.",
                reply_to_message_id=update.message.message_id,
            )
            logger.warning(f"No potential targets found in chat {chat.id}")
            return

        # Log all potential targets
        logger.info(
            f"Potential targets in chat {chat.id}: "
            f"{len(potential_targets)} users - {potential_targets}"
        )

        # Get detailed info about potential targets for logging
        target_names = []
        for uid in potential_targets:
            try:
                member = await chat.get_member(uid)
                username = (
                    f"@{member.user.username}"
                    if member.user.username
                    else "no_username"
                )
                target_names.append(f"{member.user.full_name} ({username}, id={uid})")
            except Exception as e:
                logger.debug(f"Could not get member info for {uid}: {e}")
                target_names.append(f"id={uid}")

        logger.info(f"Available targets: {', '.join(target_names)}")

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

        # Mark command as used (start 1h cooldown)
        cooldown_service.mark_used("kill_random")

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
