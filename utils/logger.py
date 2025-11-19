import logging
import sys
import os
from logging.handlers import RotatingFileHandler
from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaDocument
from utils.decorators import sudo_only
from utils.helpers import get_lang
from config import OWNER_ID

# Global logger control
LOGGING_ENABLED = True

def setup_logger():
    """Setup logging configuration"""
    # Create logs directory
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    # Configure logging format
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_format)
    console_handler.setLevel(logging.INFO)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        "logs/bot.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(log_format)
    file_handler.setLevel(logging.DEBUG)
    
    # Error log handler
    error_handler = RotatingFileHandler(
        "logs/error.log",
        maxBytes=5*1024*1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setFormatter(log_format)
    error_handler.setLevel(logging.ERROR)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    
    # Suppress pyrogram debug logs
    logging.getLogger("pyrogram").setLevel(logging.WARNING)

def set_logging_enabled(enabled: bool):
    """Enable or disable logging globally"""
    global LOGGING_ENABLED
    LOGGING_ENABLED = enabled
    
    root_logger = logging.getLogger()
    if enabled:
        root_logger.setLevel(logging.INFO)
    else:
        root_logger.setLevel(logging.CRITICAL)

def is_logging_enabled() -> bool:
    """Check if logging is enabled"""
    return LOGGING_ENABLED

@Client.on_message(filters.command("logs"))
@sudo_only
async def send_logs(client: Client, message: Message):
    """Send log files to sudo users"""
    lang = "en"
    
    try:
        # Check if log files exist
        log_files = []
        
        if os.path.exists("logs/bot.log"):
            log_files.append("logs/bot.log")
        
        if os.path.exists("logs/error.log"):
            log_files.append("logs/error.log")
        
        if not log_files:
            await message.reply_text(get_lang("no_logs_found", lang))
            return
        
        status_msg = await message.reply_text(get_lang("sending_logs", lang))
        
        # Send log files
        media_group = []
        for log_file in log_files:
            # Get file size
            file_size = os.path.getsize(log_file)
            file_size_mb = file_size / (1024 * 1024)
            
            caption = f"📄 {os.path.basename(log_file)}
"
            caption += f"📊 Size: {file_size_mb:.2f} MB"
            
            if len(log_files) > 1:
                media_group.append(InputMediaDocument(log_file, caption=caption))
            else:
                await message.reply_document(log_file, caption=caption)
        
        if media_group:
            await message.reply_media_group(media_group)
        
        await status_msg.delete()
    
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error sending logs: {e}")
        await message.reply_text(get_lang("error_occurred", lang))

@Client.on_message(filters.command("logger"))
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
