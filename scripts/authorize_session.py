"""Script to authorize Pyrogram session locally before running Docker"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import bot modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from pyrogram import Client  # noqa: E402

from bot.config import settings  # noqa: E402


async def authorize():
    """Authorize Pyrogram client and create session file"""
    print("=== Telegram Client Authorization ===")
    print(f"API ID: {settings.API_ID}")
    print(f"Session name: {settings.SESSION_NAME}")
    print(f"Session will be saved to: ./data/{settings.SESSION_NAME}.session")
    print()

    # Create data directory if it doesn't exist
    Path("./data").mkdir(exist_ok=True)

    client = Client(
        name=settings.SESSION_NAME,
        api_id=settings.API_ID,
        api_hash=settings.API_HASH,
        workdir="./data",
    )

    try:
        await client.start()
        me = await client.get_me()
        print()
        print("✅ Authorization successful!")
        print(f"Logged in as: {me.first_name} {me.last_name or ''} (@{me.username})")
        print(f"Phone: {me.phone_number}")
        print()
        print(f"Session file created: ./data/{settings.SESSION_NAME}.session")
        print("You can now run the bot with docker-compose.")
        await client.stop()
    except Exception as e:
        print(f"❌ Authorization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(authorize())
