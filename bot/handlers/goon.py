"""Goon commands handler: /goon and /top_gooners"""

import logging
import random
from datetime import datetime
from typing import Optional

import aiohttp
from zoneinfo import ZoneInfo
from telegram import Chat, Update
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.services.goon_stats_service import goon_stats_service

logger = logging.getLogger(__name__)


NSFW_TAGS = ["waifu", "neko", "trap", "blowjob"]


async def _fetch_waifu_url(tag: str) -> Optional[str]:
    api_url = f"https://api.waifu.pics/nsfw/{tag}"
    timeout = aiohttp.ClientTimeout(total=7)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(api_url) as resp:
                if resp.status != 200:
                    logger.warning(f"Failed to fetch waifu url for tag={tag}: status={resp.status}")
                    return None
                data = await resp.json()
                url = data.get("url")
                if isinstance(url, str) and url.startswith("http"):
                    return url
                logger.warning("Invalid response structure from waifu.pics nsfw API")
                return None
    except Exception as e:
        logger.error(f"Error fetching waifu url for tag={tag}: {e}")
        return None


async def goon_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat or not update.message:
        return

    # Optional: prevent in private if desired; currently allow everywhere
    tag = random.choice(NSFW_TAGS)
    image_url = await _fetch_waifu_url(tag)
    if not image_url:
        await update.message.reply_text(
            "❌ Не удалось получить картинку, попробуйте позже",
            reply_to_message_id=update.message.message_id,
        )
        return

    try:
        msg = await context.bot.send_photo(
            chat_id=chat.id, photo=image_url, caption=f"NSFW", has_spoiler=True
        )
    except Exception as e:
        logger.warning(f"Failed to send goon photo to chat {chat.id}: {e}")
        await update.message.reply_text(
            "❌ Не удалось отправить картинку",
            reply_to_message_id=update.message.message_id,
        )
        return

    # Record stat for current MSK month
    try:
        goon_stats_service.record_usage(chat_id=chat.id, user_id=user.id, when=datetime.now(ZoneInfo("Europe/Moscow")))
    except Exception as e:
        logger.warning(f"Failed to record goon stat: {e}")


def _month_key_now_msk() -> str:
    now_msk = datetime.now(ZoneInfo("Europe/Moscow"))
    return now_msk.strftime("%Y-%m")


async def top_gooners_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if not chat or not update.message:
        return

    # Top is per-chat
    month_key = _month_key_now_msk()
    top = goon_stats_service.get_top_for_month(month_key, chat.id, top_n=10)
    if not top:
        await update.message.reply_text(
            "За этот месяц пока нет данных.",
            reply_to_message_id=update.message.message_id,
        )
        return

    # Try to resolve display names (may require extra API calls)
    lines: list[str] = [f"🏆 Топ дрочил за месяц:"]
    rank = 1
    for entry in top:
        display = f"id={entry.user_id}"
        try:
            member = await chat.get_member(entry.user_id)
            if member and member.user:
                if member.user.username:
                    display = f"@{member.user.username}"
                else:
                    display = member.user.full_name
        except Exception:
            # Ignore failures; keep id fallback
            pass
        lines.append(f"{rank}. {display} — {entry.count}")
        rank += 1

    await update.message.reply_text(
        "\n".join(lines), reply_to_message_id=update.message.message_id
    )


def register_goon_handlers(app: Application) -> None:
    app.add_handler(CommandHandler("goon", goon_command))
    app.add_handler(CommandHandler("top_gooners", top_gooners_command))
    logger.info("Goon handlers registered")


