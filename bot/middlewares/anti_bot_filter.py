"""Middleware to delete interactions with a specific bot"""

import logging
from typing import Iterable, Optional

from telegram import Message, MessageEntity, Update
from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter, TimedOut
from telegram.ext import Application, ContextTypes, TypeHandler

logger = logging.getLogger(__name__)


TARGET_BOT_USERNAME = "twoonethreein_bot"  # can be provided with or without leading '@'
# Normalize to plain username (no '@', lowercase)
TARGET_BOT_USERNAME = TARGET_BOT_USERNAME.lstrip("@").lower()


def _iter_entities(message: Message) -> Iterable[tuple[str, MessageEntity]]:
    """Yield (text, entity) pairs for both text and caption entities."""
    if message.text and message.entities:
        for entity in message.entities:
            yield message.text, entity
    if message.caption and message.caption_entities:
        for entity in message.caption_entities:
            yield message.caption, entity


def _entity_text(text: str, entity: MessageEntity) -> Optional[str]:
    """Extract the substring corresponding to an entity.

    Returns None if the slice is invalid for any reason.
    """
    try:
        return text[entity.offset : entity.offset + entity.length]
    except Exception:
        return None


def _mentions_target_bot(message: Message) -> Optional[str]:
    """Check whether message mentions or addresses the target bot.

    Returns a reason: "mention" or "bot_command"; otherwise None.
    """
    for text, entity in _iter_entities(message):
        # Compare by string type to avoid version-specific enum differences
        etype = str(getattr(entity, "type", ""))
        if etype in {"mention", "bot_command"}:
            piece = _entity_text(text, entity)
            if not piece:
                continue
            lower_piece = piece.lower()
            # Handles '@twoonethreein_bot' and '/cmd@twoonethreein_bot'
            if TARGET_BOT_USERNAME in lower_piece.lstrip("@"):
                return etype
    return None


def _is_from_target_bot(message: Message) -> Optional[str]:
    """Check whether the message originates from the target bot.

    Returns a reason: "from_user", "forward_from", or "via_bot"; otherwise None.
    """
    if message.from_user and message.from_user.is_bot:
        if (message.from_user.username or "").lower() == TARGET_BOT_USERNAME:
            return "from_user"

    # Forwarded messages from the target bot
    if message.forward_from and message.forward_from.is_bot:
        if (message.forward_from.username or "").lower() == TARGET_BOT_USERNAME:
            return "forward_from"

    # Inline messages sent via the target bot
    if (
        message.via_bot
        and (message.via_bot.username or "").lower() == TARGET_BOT_USERNAME
    ):
        return "via_bot"

    return None


async def filter_twoonethreein(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Delete messages calling or sent by the specific bot.

    - Deletes any message from @twoonethreein_bot
    - Deletes any message mentioning or addressing @twoonethreein_bot
    """
    message = update.effective_message
    if not message:
        return

    try:
        to_delete = False
        match_reason: Optional[str] = None

        # Direct, forwarded, or via-bot from target
        source_reason = _is_from_target_bot(message)
        if source_reason is not None:
            to_delete = True
            match_reason = source_reason

        # Mentions or commands referencing target
        if not to_delete:
            mention_reason = _mentions_target_bot(message)
            if mention_reason is not None:
                to_delete = True
                match_reason = mention_reason

        # Replies to the target bot's message
        if (
            not to_delete
            and message.reply_to_message is not None
            and _is_from_target_bot(message.reply_to_message) is not None
        ):
            to_delete = True
            match_reason = "reply_to_bot"

        if to_delete:
            await message.delete()
            logger.info(
                "Deleted message %s in chat %s (reason=%s)",
                message.message_id,
                message.chat_id if message.chat else "unknown",
                match_reason or "unknown",
            )
    except Forbidden:
        logger.warning(
            "Delete failed (Forbidden) for msg %s in chat %s (reason=%s): "
            "missing permission to delete messages",
            message.message_id if message else "unknown",
            message.chat_id if message and message.chat else "unknown",
            match_reason or "unknown",
        )
    except BadRequest as exc:
        logger.warning(
            "Delete failed (BadRequest) for msg %s in chat %s (reason=%s): %s",
            message.message_id if message else "unknown",
            message.chat_id if message and message.chat else "unknown",
            match_reason or "unknown",
            str(exc),
        )
    except RetryAfter as exc:
        logger.warning(
            "Delete failed (RetryAfter %.1fs) for msg %s in chat %s (reason=%s)",
            getattr(exc, "retry_after", 0.0),
            message.message_id if message else "unknown",
            message.chat_id if message and message.chat else "unknown",
            match_reason or "unknown",
        )
    except (TimedOut, NetworkError) as exc:
        logger.warning(
            "Delete failed (Network/Timeout) for msg %s in chat %s (reason=%s): %s",
            message.message_id if message else "unknown",
            message.chat_id if message and message.chat else "unknown",
            match_reason or "unknown",
            str(exc),
        )
    except Exception as exc:
        # Deletion may fail due to other reasons
        logger.warning(
            "Delete failed (Unexpected) for msg %s in chat %s (reason=%s): %s",
            message.message_id if message else "unknown",
            message.chat_id if message and message.chat else "unknown",
            match_reason or "unknown",
            str(exc),
        )


def register_anti_bot_filter(app: Application) -> None:
    """Register anti-bot filter to run before other handlers."""
    app.add_handler(TypeHandler(Update, filter_twoonethreein), group=-2)
    logger.info("Anti-bot filter middleware registered")
