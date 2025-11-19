import asyncio
import logging
import os
import sys
from pyrogram import Client, idle
from pyrogram.enums import ParseMode
from config import API_ID, API_HASH, BOT_TOKEN, BOT_USERNAME, LOGGER_ID
from utils.database import Database
from utils.cache import init_cache, get_cache
from utils.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)

app = Client(
    "guard_x",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="plugins"),
    parse_mode=ParseMode.HTML
)

db = Database()
cache = None

async def _send_startup_message():
    try:
        text = f"{BOT_USERNAME} started successfully 🚀"
        await app.send_message(LOGGER_ID, text)
        logger.info("Startup message sent to logger id")
    except Exception as e:
        logger.exception(f"Failed to send startup message to logger id: {e}")

async def main():
    global cache
    try:
        await db.connect()
        await init_cache(db)
        cache = get_cache()
        await app.start()
        bot_info = await app.get_me()
        logger.info(f"Bot started successfully: @{bot_info.username}")
        await _send_startup_message()
        await idle()
    except Exception as e:
        logger.exception(f"Error starting bot: {e}")
    finally:
        try:
            await app.stop()
        except Exception:
            pass
        try:
            if getattr(db, "client", None):
                db.client.close()
        except Exception:
            pass
        logger.info("Bot stopped")

if __name__ == "__main__":
    asyncio.run(main())
