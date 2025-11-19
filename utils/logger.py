import logging
import sys
import os
import glob
from logging.handlers import RotatingFileHandler
from typing import List
from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaDocument
from utils.decorators import sudo_only
from utils.helpers import get_lang

LOGGING_ENABLED = False
LOGS_DIR = "logs"
LOG_BASE_FILENAME = "log.txt"


def setup_logger():
    """Setup logging configuration"""
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)

    log_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    console_handler.setLevel(logging.INFO)

    # RotatingFileHandler still writes to the configured active file (you can change filename elsewhere)
    file_handler = RotatingFileHandler(
        os.path.join(LOGS_DIR, LOG_BASE_FILENAME),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(log_format)
    file_handler.setLevel(logging.DEBUG)

    error_handler = RotatingFileHandler(
        os.path.join(LOGS_DIR, "error.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    error_handler.setFormatter(log_format)
    error_handler.setLevel(logging.ERROR)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)

    logging.getLogger("pyrogram").setLevel(logging.WARNING)


def set_logging_enabled(enabled: bool):
    """Enable or disable logging globally"""
    global LOGGING_ENABLED
    LOGGING_ENABLED = enabled

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO if enabled else logging.CRITICAL)


def is_logging_enabled() -> bool:
    """Check if logging is enabled"""
    return LOGGING_ENABLED


def _collect_log_files(directory: str = LOGS_DIR) -> List[str]:
    """
    Prefer files that match LOG_BASE_FILENAME and its rotated variants (e.g. log.txt, log.txt.1, log.txt.*).
    If none found, fall back to returning all regular files in directory.
    Sorted by modification time (oldest first).
    """
    if not os.path.exists(directory):
        return []

    # look for log.txt variants first
    pattern = os.path.join(directory, LOG_BASE_FILENAME + "*")
    matched = glob.glob(pattern)
    matched = [p for p in matched if os.path.isfile(p)]

    if matched:
        matched.sort(key=lambda p: os.path.getmtime(p))
        return matched

    # fallback: include all files in logs directory
    all_files = [
        os.path.join(directory, name)
        for name in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, name))
    ]
    all_files.sort(key=lambda p: os.path.getmtime(p))
    return all_files


def _chunk_list(lst: List, n: int):
    """Yield successive n-sized chunks from list."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


@Client.on_message(filters.command(["logs", "getlogs"]) & filters.private)
@sudo_only
async def send_logs(client: Client, message: Message):
    """
    Send prioritized log.txt* files if present; otherwise send all files inside logs/.
    Single file -> reply_document (keeps caption). Multiple files -> reply_media_group in batches of 10.
    """
    lang = "en"
    logger = logging.getLogger(__name__)

    try:
        log_files = _collect_log_files(LOGS_DIR)

        if not log_files:
            await message.reply_text(get_lang("no_logs_found", lang))
            return

        status_msg = await message.reply_text(get_lang("sending_logs", lang))

        # Single file: send with reply_document to preserve caption
        if len(log_files) == 1:
            log_file = log_files[0]
            size_mb = os.path.getsize(log_file) / (1024 * 1024)
            caption = (
                f"📄 {os.path.basename(log_file)}\n"
                f"📊 Size: {size_mb:.2f} MB"
            )
            await message.reply_document(log_file, caption=caption)

        else:
            # Send in media-group batches (Telegram limit: 10 per media group)
            for chunk in _chunk_list(log_files, 10):
                media_group = []
                for log_file in chunk:
                    size_mb = os.path.getsize(log_file) / (1024 * 1024)
                    caption = (
                        f"📄 {os.path.basename(log_file)}\n"
                        f"📊 Size: {size_mb:.2f} MB"
                    )
                    media_group.append(InputMediaDocument(log_file, caption=caption))

                await message.reply_media_group(media_group)

        await status_msg.delete()

    except Exception as e:
        logger.error(f"Error sending logs: {e}", exc_info=True)
        await message.reply_text(get_lang("error_occurred", lang))


@Client.on_message(filters.command("logger") & filters.private)
@sudo_only
async def toggle_logger(client: Client, message: Message):
    """Toggle logging on/off globally"""
    lang = "en"

    if len(message.command) < 2:
        status = "ON" if is_logging_enabled() else "OFF"
        await message.reply_text(get_lang("logger_status", lang, status=status))
        return

    action = message.command[1].lower()

    if action == "on":
        set_logging_enabled(True)
        await message.reply_text(get_lang("logger_enabled", lang))
    elif action == "off":
        set_logging_enabled(False)
        await message.reply_text(get_lang("logger_disabled", lang))
    else:
        await message.reply_text(get_lang("logger_usage", lang))
