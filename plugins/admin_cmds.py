from pyrogram import Client, filters
from pyrogram.types import Message
from utils.decorators import admin_only
from utils.helpers import get_lang, is_creator
from utils.database import Database
from utils.cache import CacheManager
from config import SUDO_USERS
import logging
import datetime

db = Database()
cache = CacheManager()
logger = logging.getLogger(__name__)


@Client.on_message(filters.command("reload") & filters.group)
@admin_only
async def reload_admins(client: Client, message: Message):
    lang = await db.get_group_language(message.chat.id)
    
    try:
        cache.clear_admins(message.chat.id)
        
        admins = [
            member.user.id async for member in client.get_chat_members(
                message.chat.id, filter="administrators"
            )
        ]
        
        cache.set_admins(message.chat.id, admins)
        
        await message.reply_text(get_lang("reload_success", lang, count=len(admins)))
    except Exception as e:
        logger.error(f"Error reloading admins in {message.chat.id}: {e}")
        await message.reply_text(get_lang("reload_failed", lang))


@Client.on_message(filters.command("autoclean") & filters.group)
@admin_only
async def toggle_autoclean(client: Client, message: Message):
    lang = await db.get_group_language(message.chat.id)
    
    if len(message.command) < 2:
        await message.reply_text(get_lang("autoclean_usage", lang))
        return
    
    status = message.command[1].lower()
    if status == "on":
        await db.set_auto_clean(message.chat.id, True)
        cache.set_setting(message.chat.id, "auto_clean", True)
        await message.reply_text(get_lang("autoclean_enabled", lang))
    elif status == "off":
        await db.set_auto_clean(message.chat.id, False)
        cache.set_setting(message.chat.id, "auto_clean", False)
        await message.reply_text(get_lang("autoclean_disabled", lang))
    else:
        await message.reply_text(get_lang("autoclean_usage", lang))


@Client.on_message(filters.command("stats") & (filters.private | filters.group))
async def show_stats(client: Client, message: Message):
    """Show bot statistics — ONLY bot owner can use this command"""
    if message.from_user.id != SUDO_USERS:
        return 
    
    lang = "en"  # owner stats usually in English
    try:
        stats = await db.get_total_stats()
        
        stats_text = get_lang("stats_header", lang) + "\n\n"
        stats_text += get_lang("stats_groups", lang, count=stats["total_groups"]) + "\n"
        stats_text += get_lang("stats_users", lang, count=stats["total_users"]) + "\n\n"
        stats_text += get_lang("stats_edit_enabled", lang, count=stats["edit_enabled"]) + "\n"
        stats_text += get_lang("stats_media_enabled", lang, count=stats["media_enabled"]) + "\n"
        stats_text += get_lang("stats_slang_enabled", lang, count=stats["slang_enabled"])
        
        await message.reply_text(stats_text)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        await message.reply_text("An error occurred while fetching stats.")


@Client.on_message(filters.command("dev"))
async def developer_info(client: Client, message: Message):
    lang = await db.get_group_language(message.chat.id) if message.chat else "en"
    dev_text = get_lang("developer_info", lang)
    await message.reply_text(dev_text, disable_web_page_preview=True)


@Client.on_message(filters.command("logadmin") & filters.group)
async def log_admin_activity(client: Client, message: Message):
    lang = await db.get_group_language(message.chat.id)
    
    if not await is_creator(client, message.chat.id, message.from_user.id):
        await message.reply_text(get_lang("creator_only", lang))
        return
    
    logs = await db.get_admin_logs(message.chat.id, limit=20)
    if not logs:
        await message.reply_text(get_lang("no_admin_logs", lang))
        return
    
    log_text = get_lang("admin_logs_header", lang) + "\n\n"
    for log in logs:
        ts = datetime.datetime.fromtimestamp(log["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
        log_text += f"⏰ {ts}\n"
        log_text += f"👤 Admin: `{log['admin_id']}`\n"
        log_text += f"📝 Action: {log['action']}\n"
        if log.get("target_user"):
            log_text += f"🎯 Target: `{log['target_user']}`\n"
        log_text += "─" * 20 + "\n"
    
    await message.reply_text(log_text)
