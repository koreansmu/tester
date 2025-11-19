import logging
import os
import glob
from logging.handlers import RotatingFileHandler
from typing import List

from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaDocument

from utils.decorators import sudo_only
from utils.helpers import get_lang

LOGS_DIR = "logs"
LOG_BASE_FILENAME = "log.txt"


def setup_logger():
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        filename=os.path.join(LOGS_DIR, LOG_BASE_FILENAME),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    error_handler = RotatingFileHandler(
        filename=os.path.join(LOGS_DIR, "error.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(console)
    root.addHandler(file_handler)
    root.addHandler(error_handler)

    logging.getLogger("pyrogram").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def _get_log_files() -> List[str]:
    if not os.path.exists(LOGS_DIR):
        return []

    pattern = os.path.join(LOGS_DIR, LOG_BASE_FILENAME + "*")
    files = glob.glob(pattern)
    files = [f for f in files if os.path.isfile(f)]

    if not files:
        files = [os.path.join(LOGS_DIR, f) for f in os.listdir(LOGS_DIR) if os.path.isfile(os.path.join(LOGS_DIR, f))]

    files.sort(key=os.path.getmtime)
    return files


def _chunks(lst: List, n: int):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


@Client.on_message(filters.command(["logs", "getlogs"]) & filters.private)
@sudo_only
async def send_logs(client: Client, message: Message):
    lang = "en"
    log_files = _get_log_files()

    if not log_files:
        await message.reply_text(get_lang("no_logs_found", lang))
        return

    status = await message.reply_text(get_lang("sending_logs", lang))

    try:
        if len(log_files) == 1:
            file_path = log_files[0]
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            caption = f"📄 {os.path.basename(file_path)}\n📊 Size: {size_mb:.2f} MB"
            await message.reply_document(file_path, caption=caption)
        else:
            for chunk in _chunks(log_files, 10):
                media = []
                for file_path in chunk:
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    caption = f"📄 {os.path.basename(file_path)}\n📊 Size: {size_mb:.2f} MB"
                    media.append(InputMediaDocument(file_path, caption=caption))
                await client.send_media_group(message.chat.id, media, reply_to_message_id=message.id)
        await status.delete()
    except Exception as e:
        logging.getLogger(__name__).error("Failed to send logs", exc_info=True)
        await message.reply_text(get_lang("error_occurred", lang))


@Client.on_message(filters.command("logger") & filters.private)
@sudo_only
async def toggle_logger(client: Client, message: Message):
    lang = "en"
    logger = logging.getLogger()

    if len(message.command) < 2:
        status = "ON" if logger.level <= logging.INFO else "OFF"
        await message.reply_text(get_lang("logger_status", lang, status=status))
        return

    arg = message.command[1].lower()

    if arg == "on":
        logger.setLevel(logging.INFO)
        await message.reply_text(get_lang("logger_enabled", lang))
    elif arg == "off":
        logger.setLevel(logging.CRITICAL)
        await message.reply_text(get_lang("logger_disabled", lang))
    else:
        await message.reply_text(get_lang("logger_usage", lang))
