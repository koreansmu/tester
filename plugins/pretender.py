from pyrogram import Client, filters
from pyrogram.types import Message
from utils.decorators import creator_only
from utils.helpers import get_lang
from utils.database import Database
from utils.cache import CacheManager
import logging

db = Database()
cache = CacheManager()
logger = logging.getLogger(__name__)

# In-memory cache: {f"{chat_id}:{user_id}": {"first_name": ..., "username": ...}}
user_data_cache = {}


@Client.on_message(filters.command("pretender") & filters.group)
@creator_only
async def toggle_pretender(client: Client, message: Message):
    lang = await db.get_group_language(message.chat.id)
    
    if len(message.command) < 2:
        await message.reply_text(get_lang("pretender_usage", lang))
        return
    
    status = message.command[1].lower()
    
    if status == "on":
        await db.set_pretender(message.chat.id, True)
        cache.set_setting(message.chat.id, "pretender_enabled", True)
        await message.reply_text(get_lang("pretender_enabled", lang))
    elif status == "off":
        await db.set_pretender(message.chat.id, False)
        cache.set_setting(message.chat.id, "pretender_enabled", False)
        await message.reply_text(get_lang("pretender_disabled", lang))
    else:
        await message.reply_text(get_lang("pretender_usage", lang))


@Client.on_message(filters.command("spretender") & filters.group)
async def check_pretender_status(client: Client, message: Message):
    lang = await db.get_group_language(message.chat.id)
    
    enabled = cache.get_setting(message.chat.id, "pretender_enabled")
    if enabled is None:
        enabled = await db.get_pretender_status(message.chat.id)
        cache.set_setting(message.chat.id, "pretender_enabled", enabled)
    
    if enabled:
        await message.reply_text(get_lang("spretender_on", lang))
    else:
        await message.reply_text(get_lang("spretender_off", lang))


@Client.on_message(filters.group & filters.text & ~filters.edited)
async def track_user_changes(client: Client, message: Message):
    try:
        enabled = cache.get_setting(message.chat.id, "pretender_enabled")
        if enabled is None:
            enabled = await db.get_pretender_status(message.chat.id)
            cache.set_setting(message.chat.id, "pretender_enabled", enabled)
        
        if not enabled:
            return
        
        user = message.from_user
        if not user:
            return
        
        cache_key = f"{message.chat.id}:{user.id}"
        current_data = {
            "first_name": user.first_name or "",
            "username": user.username or None
        }
        
        old_data = user_data_cache.get(cache_key)
        if old_data:
            lang = await db.get_group_language(message.chat.id)
            changes = []
            
            if old_data["first_name"] != current_data["first_name"]:
                changes.append(get_lang(
                    "name_changed",
                    lang,
                    old=old_data["first_name"] or "None",
                    new=current_data["first_name"] or "None"
                ))
            
            if old_data["username"] != current_data["username"]:
                old_un = old_data["username"] or "None"
                new_un = current_data["username"] or "None"
                changes.append(get_lang(
                    "username_changed",
                    lang,
                    old=old_un,
                    new=new_un
                ))
            
            if changes:
                alert_text = get_lang("pretender_alert", lang, user=user.mention)
                alert_text += "\n\n" + "\n".join(changes)
                await message.reply_text(alert_text, disable_web_page_preview=True)
        
        # Always update the cache (even for first message from user)
        user_data_cache[cache_key] = current_data.copy()
    
    except Exception as e:
        logger.error(f"Error in pretender detection: {e}")
