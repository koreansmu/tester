import asyncio
import logging
from pyrogram import Client, idle
from pyrogram.enums import ParseMode
from config import API_ID, API_HASH, BOT_TOKEN
from utils.database import Database
from utils.cache import CacheManager
from utils.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)

# Initialize bot
app = Client(
    "guard_x_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="plugins"),
    parse_mode=ParseMode.HTML
)

# Global instances
db = Database()
cache = CacheManager()

async def main():
    """Main function to start the bot"""
    try:
        await app.start()
        bot_info = await app.get_me()
        logger.info(f"Bot started successfully: @{bot_info.username}")
        
        await cache.load_from_db(db)
        logger.info("Cache loaded successfully")
        
        await idle()
        
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
    finally:
        await app.stop()
        logger.info("Bot stopped")

if __name__ == "__main__":
    asyncio.run(main())
