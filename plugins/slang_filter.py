from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from utils.decorators import admin_only
from utils.helpers import get_lang, is_admin, load_slang_words
from utils.database import Database
from utils.cache import CacheManager
from config import SUPPORT_CHAT
import logging

db = Database()
cache = CacheManager()
logger = logging.getLogger(__name__)

SLANG_WORDS = load_slang_words()

@Client.on_message(filters.command("slang") & filters.group)
@admin_only
async def toggle_slang(client: Client, message: Message):
    lang = await db.get_group_language(message.chat.id)
    if len(message.command) < 2:
        await message.reply_text(get_lang("slang_usage", lang))
        return
    status = message.command[1].lower()
    if status == "on":
        await db.set_slang_filter(message.chat.id, True)
        cache.set_setting(message.chat.id, "slang_enabled", True)
        await message.reply_text(get_lang("slang_enabled", lang))
    elif status == "off":
        await db.set_slang_filter(message.chat.id, False)
        cache.set_setting(message.chat.id, "slang_enabled", False)
        await message.reply_text(get_lang("slang_disabled", lang))
    else:
        await message.reply_text(get_lang("slang_usage", lang))

@Client.on_message(filters.group & filters.text)
async def check_slang(client: Client, message: Message):
    try:
        if message.edit_date:
            return
        enabled = cache.get_setting(message.chat.id, "slang_enabled")
        if enabled is None:
            enabled = await db.get_slang_status(message.chat.id)
            cache.set_setting(message.chat.id, "slang_enabled", enabled)
        if not enabled:
            return
        user_is_admin = await is_admin(client, message.chat.id, message.from_user.id)
        if user_is_admin:
            is_auth = cache.get_auth(message.chat.id, message.from_user.id, "slang")
            if is_auth is None:
                is_auth = await db.is_slang_authorized(message.chat.id, message.from_user.id)
                cache.set_auth(message.chat.id, message.from_user.id, "slang", is_auth)
            if is_auth:
                return
        text = message.text.lower()
        found_words = [word for word in SLANG_WORDS if word in text]
        if found_words:
            lang = await db.get_group_language(message.chat.id)
            await message.delete()
            spoiler_words = " ".join(f"||{word}||" for word in found_words)
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🚨 ʀᴇᴘᴏʀᴛ sᴘᴀᴍ", url=SUPPORT_CHAT)
            ]])
            warning_text = get_lang(
                "slang_detected",
                lang,
                user=message.from_user.mention,
                words=spoiler_words
            )
            await client.send_message(
                message.chat.id,
                warning_text,
                reply_markup=keyboard
            )
    except Exception as e:
        logger.error(f"Error checking slang: {e}")

@Client.on_message(filters.command("sauth") & filters.group)
@admin_only
async def slang_auth(client: Client, message: Message):
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
        await message.reply_text(get_lang("sauth_usage", lang))
        return
    await db.add_slang_auth(message.chat.id, user_id)
    cache.set_auth(message.chat.id, user_id, "slang", True)
    await message.reply_text(get_lang("sauth_success", lang))

@Client.on_message(filters.command("sunauth") & filters.group)
@admin_only
async def slang_unauth(client: Client, message: Message):
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
        await message.reply_text(get_lang("sunauth_usage", lang))
        return
    await db.remove_slang_auth(message.chat.id, user_id)
    cache.set_auth(message.chat.id, user_id, "slang", False)
    await message.reply_text(get_lang("sunauth_success", lang))

@Client.on_message(filters.command("sauthlist") & filters.group)
async def slang_auth_list(client: Client, message: Message):
    lang = await db.get_group_language(message.chat.id)
    auth_users = await db.get_slang_auth_list(message.chat.id)
    if not auth_users:
        await message.reply_text(get_lang("no_auth_users", lang))
        return
    text = get_lang("sauthlist_header", lang) + "\n\n"
    for idx, user in enumerate(auth_users, 1):
        text += f"{idx}. User ID: `{user['user_id']}`\n"
    await message.reply_text(text)
