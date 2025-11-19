import asyncio
import importlib
import logging
import os
from pyrogram import idle, Client
from pyrogram.enums import ParseMode
from config import API_ID, API_HASH, BOT_TOKEN, BOT_USERNAME, LOGGER_ID
from utils.database import Database
from utils.cache import init_cache
from utils.logger import setup_logger

setup_logger()
logger = logging.getLogger(__name__)

db = None
cache = None
app = None

PLUGINS_ROOT = "plugins"

async def _send_startup_message(client):
    try:
        text = f"{BOT_USERNAME} started successfully 🚀"
        await client.send_message(LOGGER_ID, text)
        logger.info("Startup message sent to logger id")
    except Exception as e:
        logger.exception("Failed to send startup message to logger id: %s", e)

def _iter_plugin_modules(root: str):
    root_path = os.path.abspath(root)
    if not os.path.isdir(root_path):
        return
    for dirpath, dirnames, filenames in os.walk(root_path):
        # skip __pycache__
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        rel_dir = os.path.relpath(dirpath, root_path)
        if rel_dir == ".":
            pkg_prefix = root
        else:
            # convert path separators to module dots
            pkg_prefix = root + "." + rel_dir.replace(os.sep, ".")
        for fname in filenames:
            if not fname.endswith(".py"):
                continue
            if fname.startswith("_"):
                continue
            mod_name = fname[:-3]
            yield f"{pkg_prefix}.{mod_name}"

def import_plugins_and_log(root: str = PLUGINS_ROOT):
    logger.info("Scanning plugins in '%s'...", root)
    mods = list(_iter_plugin_modules(root))
    if not mods:
        logger.warning("No plugin modules found in '%s'.", root)
        return
    for module in sorted(mods):
        try:
            importlib.import_module(module)
            logger.info("Loaded plugin: %s", module)
        except Exception as e:
            logger.exception("Failed to import plugin %s: %s", module, e)

async def main():
    global db, cache, app

    db = Database()
    try:
        await db.connect()
        logger.info("Connected to database")
    except Exception as e:
        logger.exception("Failed to connect to database: %s", e)
        return

    try:
        cache = await init_cache(db)
        logger.info("Cache initialized")
    except Exception as e:
        logger.exception("Failed to initialize cache: %s", e)
        # continue — cache failure shouldn't block bot start

    # import plugins explicitly and log each
    import_plugins_and_log(PLUGINS_ROOT)

    app = Client(
        "guard_x",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        parse_mode=ParseMode.HTML,
        # don't pass plugins dict because we import plugins manually above
    )

    try:
        await app.start()
        bot_info = await app.get_me()
        logger.info("Bot started successfully: @%s (id=%s)", getattr(bot_info, "username", ""), getattr(bot_info, "id", "unknown"))
        await _send_startup_message(app)
        await idle()
    except Exception as e:
        logger.exception("Error starting bot: %s", e)
    finally:
        try:
            await app.stop()
        except Exception:
            pass
        try:
            if db and getattr(db, "client", None):
                db.client.close()
        except Exception:
            pass
        logger.info("Bot stopped")

if __name__ == "__main__":
    asyncio.run(main())
