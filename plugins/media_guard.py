from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from utils.decorators import admin_only
from utils.helpers import get_lang, is_admin
from utils.database import Database
from utils.cache import CacheManager
from config import SUPPORT_CHAT, LOGGER_ID
import asyncio
import logging

db = Database()
cache = CacheManager()
logger = logging.getLogger(__name__)

# Store scheduled deletions (optional, not used in current code)
scheduled_deletions = {}

@Client.on_message(filters.command("setdelay") & filters.group)
@admin_only
async def set_media_delay(client: Client, message: Message):
    lang = await db.get_group_language(message.chat.id)
    
    try:
        if len(message.command) < 2:
            await message.reply_text(get_lang("setdelay_usage", lang))
            return
        
        delay = int(message.command[1])
        if delay < 0:
            await message.reply_text(get_lang("invalid_delay", lang))
            return
        
        await db.set_media_delay(message.chat.id, delay)
        cache.set_setting(message.chat.id, "media_delay", delay)
        
        if LOGGER_ID:
            admin_name = message.from_user.first_name
            admin_username = f"@{message.from_user.username}" if message.from_user.username else "No username"
            log_msg = f"⚙️ **Media Guard Enabled**\n\n"
            log_msg += f"👤 Admin: {admin_name} ({admin_username})\n"
            log_msg += f"💬 Group: {message.chat.title}\n"
            log_msg += f"⏱ Delay: {delay} minutes"
            await client.send_message(LOGGER_ID, log_msg)
        
        await message.reply_text(get_lang("setdelay_success", lang, delay=delay))
    
    except ValueError:
        await message.reply_text(get_lang("invalid_number", lang))
    except Exception as e:
        logger.error(f"Error in setdelay: {e}")
        await message.reply_text(get_lang("error_occurred", lang))


@Client.on_message(filters.command("getdelay") & filters.group)
async def get_media_delay(client: Client, message: Message):
    lang = await db.get_group_language(message.chat.id)
    
    delay = cache.get_setting(message.chat.id, "media_delay")
    if delay is None:
        delay = await db.get_media_delay(message.chat.id)
        if delay:
            cache.set_setting(message.chat.id, "media_delay", delay)
    
    if delay:
        await message.reply_text(get_lang("getdelay_enabled", lang, delay=delay))
    else:
        await message.reply_text(get_lang("getdelay_disabled", lang))


@Client.on_message(
    filters.group &
    (filters.photo | filters.video | filters.animation | filters.sticker | filters.document)
)
async def handle_media(client: Client, message: Message):
    try:
        # Check gban
        is_gbanned = cache.get_gban(message.from_user.id)
        if is_gbanned is None:
            is_gbanned = await db.is_gbanned(message.from_user.id)
            cache.set_gban(message.from_user.id, is_gbanned)
        
        if is_gbanned:
            await message.delete()
            return
        
        # Get delay
        delay = cache.get_setting(message.chat.id, "media_delay")
        if delay is None:
            delay = await db.get_media_delay(message.chat.id)
            if delay:
                cache.set_setting(message.chat.id, "media_delay", delay)
        
        if not delay:
            return
        
        # Check if user is admin
        user_is_admin = await is_admin(client, message.chat.id, message.from_user.id)
        if user_is_admin:
            is_auth = cache.get_auth(message.chat.id, message.from_user.id, "media")
            if is_auth is None:
                is_auth = await db.is_media_authorized(message.chat.id, message.from_user.id)
                cache.set_auth(message.chat.id, message.from_user.id, "media", is_auth)
            
            if is_auth:
                return  # Authorized admin → keep media
        
        # Not authorized → warn and delete after delay
        lang = await db.get_group_language(message.chat.id)
        
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🚨 ʀᴇᴘᴏʀᴛ sᴘᴀᴍ ?", url=SUPPORT_CHAT)
        ]])
        
        warning_msg = await message.reply_text(
            get_lang("media_warning", lang, user=message.from_user.mention, delay=delay),
            reply_markup=keyboard
        )
        
        await asyncio.sleep(delay * 60)
        
        try:
            await message.delete()
            await warning_msg.delete()
        except:
            pass
    
    except Exception as e:
        logger.error(f"Error handling media: {e}")


@Client.on_message(filters.command("mauth") & filters.group)
@admin_only
async def media_auth(client: Client, message: Message):
    lang = await db.get_group_language(message.chat.id)
    
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    elif len(message.command) > 1:
        try:
            user_id = int(message.command[1])
        except ValueError:
            await message.reply_text(get_lang("invalid_user", lang))
            return
    else:
        await message.reply_text(get_lang("mauth_usage", lang))
        return
    
    await db.add_media_auth(message.chat.id, user_id)
    cache.set_auth(message.chat.id, user_id, "media", True)
    await db.log_admin_action(message.chat.id, message.from_user.id, "media_auth", user_id)
    
    await message.reply_text(get_lang("mauth_success", lang))


@Client.on_message(filters.command("munauth") & filters.group)
@admin_only
async def media_unauth(client: Client, message: Message):
    lang = await db.get_group_language(message.chat.id)
    
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    elif len(message.command) > 1:
        try:
            user_id = int(message.command[1])
        except ValueError:
            await message.reply_text(get_lang("invalid_user", lang))
            return
    else:
        await message.reply_text(get_lang("munauth_usage", lang))
        return
    
    await db.remove_media_auth(message.chat.id, user_id)
    cache.set_auth(message.chat.id, user_id, "media", False)
    
    await message.reply_text(get_lang("munauth_success", lang))


@Client.on_message(filters.command("mauthlist") & filters.group)
async def media_auth_list(client: Client, message: Message):
    lang = await db.get_group_language(message.chat.id)
    
    auth_users = await db.get_media_auth_list(message.chat.id)
    
    if not auth_users:
        await message.reply_text(get_lang("no_auth_users", lang))
        return
    
    text = get_lang("mauthlist_header", lang) + "\n\n"
    for idx, user in enumerate(auth_users, 1):
        text += f"{idx}. User ID: `{user['user_id']}`\n"
    
    await message.reply_text(text)
