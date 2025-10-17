"""Reel command handler: fetch random Instagram reel and send video"""

import logging
import re
import asyncio
import time
import secrets
from pathlib import Path
from typing import Optional
from collections import deque

import aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.config import settings
from bot.middlewares import rate_limiter

logger = logging.getLogger(__name__)


RANDOM_REEL_URL = "https://www.randomreel.com/"
RANDOM_REEL_API_URL = "https://www.randomreel.com/api/reel"
RECENT_REELS = deque(maxlen=10)


async def _fetch_random_instagram_reel_url(attempts: int = 3) -> Optional[str]:
    """Fetch randomreel page and extract an Instagram reel URL from anchor href.

    Returns:
        First matched Instagram reel URL, or None if not found/failed.
    """
    timeout = aiohttp.ClientTimeout(total=8)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        # Strong cache busting on request side
        "Cache-Control": "no-cache, no-store, max-age=0, must-revalidate",
        "Pragma": "no-cache",
    }

    pattern = re.compile(r'href="(https?://www\.instagram\.com/reels?/[^"\s>]+)"')

    for _ in range(max(1, attempts)):
        params = {"r": secrets.token_hex(8), "ts": str(int(time.time() * 1000))}
        try:
            async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
                # 1) Prefer JSON API
                try:
                    async with session.get(
                        RANDOM_REEL_API_URL,
                        params=params,
                        headers={"Accept": "application/json"},
                    ) as api_resp:
                        if api_resp.status == 200:
                            # content_type=None allows parsing even if server mislabels
                            data = await api_resp.json(content_type=None)
                            reel_id = data.get("id") if isinstance(data, dict) else None
                            if isinstance(reel_id, str) and reel_id:
                                url = f"https://www.instagram.com/reel/{reel_id}"
                                if url not in RECENT_REELS:
                                    RECENT_REELS.append(url)
                                    return url
                                # If duplicate, keep trying
                except Exception as e:
                    logger.warning(f"randomreel API fetch failed: {e}")

                # 2) Fallback to HTML page scraping
                try:
                    async with session.get(RANDOM_REEL_URL, params=params) as resp:
                        if resp.status != 200:
                            logger.warning(
                                f"randomreel.com request failed: status={resp.status}"
                            )
                            continue
                        html_text = await resp.text(errors="ignore")
                except Exception as e:
                    logger.error(f"Error fetching {RANDOM_REEL_URL}: {e}")
                    continue

                match = pattern.search(html_text)
                if match:
                    url = match.group(1)
                    # Basic de-duplication: avoid immediately repeated reels
                    if url in RECENT_REELS:
                        continue
                    RECENT_REELS.append(url)
                    return url
        except Exception as e:
            logger.error(f"Session error when fetching random reel: {e}")
            continue

    logger.warning("No Instagram reel URL found on randomreel.com page after retries")
    return None


async def _download_reel_with_ytdlp(url: str, download_dir: Path) -> Optional[Path]:
    """Download the reel via yt-dlp into download_dir and return the file path."""
    try:
        # Import inside function to avoid hard dependency at import time for tests
        import yt_dlp  # type: ignore

        download_dir.mkdir(parents=True, exist_ok=True)

        def _blocking_download() -> Optional[Path]:
            ydl_opts = {
                # save as <id>.<ext> inside download_dir
                "outtmpl": str(download_dir / "%(id)s.%(ext)s"),
                # Prefer a single MP4 file to avoid merging dependencies
                "format": "best[ext=mp4]/best",
                "noplaylist": True,
                "quiet": True,
                "retries": 2,
                "nocheckcertificate": True,
                # Reduce noise; do not write cache inside image
                "cachedir": False,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # type: ignore[attr-defined]
                info = ydl.extract_info(url, download=True)
                if not info:
                    return None
                filename = ydl.prepare_filename(info)
                path = Path(filename)
                if path.exists():
                    return path
                # Fallback: try ext from info
                ext = info.get("ext") if isinstance(info, dict) else None
                if ext:
                    alt = download_dir / f"{info.get('id')}.{ext}"
                    return alt if alt.exists() else None
                return None

        return await asyncio.to_thread(_blocking_download)
    except Exception as e:
        logger.error(f"yt-dlp download error: {e}")
        return None


async def reel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /reel command: fetch random reel, download, and send as video."""
    user = update.effective_user
    message = update.message
    chat = update.effective_chat
    if not user or not message or not chat:
        return

    # Rate limit per user
    if not rate_limiter.is_allowed(user.id):
        remaining = rate_limiter.get_remaining_cooldown(user.id)
        await message.reply_text(
            f"⏳ Подожди {remaining:.1f} сек перед следующим запросом",
            reply_to_message_id=message.message_id,
        )
        return

    logger.info(f"User {user.id} requested /reel")

    max_overall_attempts = 5
    download_dir = Path(settings.STORAGE_PATH) / "reels"

    for overall_attempt in range(max_overall_attempts):
        reel_url = await _fetch_random_instagram_reel_url()
        if not reel_url:
            # Try next attempt to get a different reel
            try:
                await asyncio.sleep(0.3)
            except Exception:
                pass
            continue

        video_path: Optional[Path] = await _download_reel_with_ytdlp(
            reel_url, download_dir
        )
        if not video_path or not video_path.exists():
            logger.warning(
                f"Attempt {overall_attempt + 1}/{max_overall_attempts}: download failed"
            )
            try:
                await asyncio.sleep(0.3)
            except Exception:
                pass
            continue

        try:
            with video_path.open("rb") as f:
                await context.bot.send_video(
                    chat_id=chat.id,
                    video=f,
                    caption="🎞️ Random Reel",
                )
            # Success — cleanup and return
            try:
                video_path.unlink(missing_ok=True)
            except Exception:
                pass
            return
        except Exception as e:
            logger.warning(
                f"Attempt {overall_attempt + 1}/{max_overall_attempts}: send failed: {e}"
            )
            # Cleanup and try a different reel next time
            try:
                video_path.unlink(missing_ok=True)
            except Exception:
                pass
            try:
                await asyncio.sleep(0.3)
            except Exception:
                pass

    # All attempts failed
    await message.reply_text(
        "❌ Не удалось отправить рилс, попробуйте позже",
        reply_to_message_id=message.message_id,
    )


def register_reel_handlers(app: Application) -> None:
    """Register /reel command handler"""
    app.add_handler(CommandHandler("reel", reel_command))
    logger.info("Reel handlers registered")


