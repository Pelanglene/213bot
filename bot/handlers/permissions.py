"""Permissions-related handlers"""

import logging

from telegram import Chat, ChatMemberAdministrator, ChatMemberOwner, Update
from telegram.ext import Application, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)


async def can_delete_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Reply whether the bot has rights to delete messages in this chat."""
    if not update.effective_chat:
        return

    chat = update.effective_chat

    # Private chats don't need admin rights to delete own messages
    if chat.type == Chat.PRIVATE:
        await update.message.reply_text("Да, в личке бот может удалять свои сообщения.")
        return

    try:
        me = await context.bot.get_chat_member(chat.id, context.bot.id)

        # Owner or Admin with delete permissions
        is_owner = isinstance(me, ChatMemberOwner)
        is_admin = isinstance(me, ChatMemberAdministrator)
        can_delete = False
        if is_owner:
            can_delete = True
        elif is_admin:
            can_delete = bool(getattr(me, "can_delete_messages", False))

        if can_delete:
            await update.message.reply_text(
                "Да, у меня есть право удалять сообщения в этом чате."
            )
        else:
            await update.message.reply_text(
                "Нет прав удалять сообщения. Дайте боту 'Delete messages' в настройках админов."
            )
    except Exception as exc:
        logger.error(f"Failed to check delete permissions: {exc}", exc_info=True)
        await update.message.reply_text("Не удалось проверить права (see logs).")


def register_permissions_handlers(app: Application) -> None:
    app.add_handler(CommandHandler("can_delete", can_delete_command))
    logger.info("Permissions handlers registered")
