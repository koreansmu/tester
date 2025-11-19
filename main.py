import asyncio
import logging
import os
import sys
from pyrogram import Client, idle
from pyrogram.enums import ParseMode
from config import API_ID, API_HASH, BOT_TOKEN, BOT_USERNAME, LOGGER_ID
from utils.database import Database
from utils.cache import CacheManager
from utils.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)

# Initialize bot
app = Client(
    "guard_x",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="plugins"),
    parse_mode=ParseMode.HTML
)

# Global instances
db = Database()
cache = CacheManager()

async def _send_startup_message():
    try:
        text = f"{BOT_USERNAME} started successfully 🚀"
        await app.send_message(LOGGER_ID, text)
        logger.info("Startup message sent to logger id")
    except Exception as e:
        logger.exception(f"Failed to send startup message to logger id: {e}")

async def main():
    """Main function to start the bot"""
    try:
        await app.start()
        bot_info = await app.get_me()
        logger.info(f"Bot started successfully: @{bot_info.username}")

        await cache.load_from_db(db)
        logger.info("Cache loaded successfully")

        await _send_startup_message()

        await idle()

    except Exception as e:
        logger.exception(f"Error starting bot: {e}")
    finally:
        try:
            await app.stop()
        except Exception:
            pass
        logger.info("Bot stopped")

if __name__ == "__main__":
    asyncio.run(main())
