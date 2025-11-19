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

@Client.on_message(filters.command("edelay") & filters.group)
@admin_only
async def set_edit_delay(client: Client, message: Message):
    lang = await db.get_group_language(message.chat.id)
    try:
        if len(message.command) < 2:
            await message.reply_text(get_lang("edelay_usage", lang))
            return
        delay = int(message.command[1])
        if delay < 0:
            await message.reply_text(get_lang("invalid_delay", lang))
            return
        await db.set_edit_delay(message.chat.id, delay)
        cache.set_setting(message.chat.id, "edit_delay", delay)
        if LOGGER_ID:
            admin_name = message.from_user.first_name
            admin_username = (
                f"@{message.from_user.username}"
                if message.from_user.username
                else admin_name
            )
            log_msg = f"✏️ **Edit Guard Enabled**\n\n"
            log_msg += f"👤 Admin: {admin_name} ({admin_username})\n"
            log_msg += f"💬 Group: {message.chat.title}\n"
            log_msg += f"⏱ Delay: {delay} minutes"
            await client.send_message(LOGGER_ID, log_msg)
        await message.reply_text(get_lang("edelay_success", lang, delay=delay))
    except ValueError:
        await message.reply_text(get_lang("invalid_number", lang))
    except Exception as e:
        logger.error(f"Error in edelay: {e}")
        await message.reply_text(get_lang("error_occurred", lang))

@Client.on_edited_message(filters.group)
async def handle_edited_message(client: Client, message: Message):
    try:
        delay = cache.get_setting(message.chat.id, "edit_delay")
        if delay is None:
            delay = await db.get_edit_delay(message.chat.id)
            if delay:
                cache.set_setting(message.chat.id, "edit_delay", delay)
        if not delay:
            return
        user_is_admin = await is_admin(client, message.chat.id, message.from_user.id)
        if user_is_admin:
            is_auth = cache.get_auth(message.chat.id, message.from_user.id, "edit")
            if is_auth is None:
                is_auth = await db.is_edit_authorized(message.chat.id, message.from_user.id)
                cache.set_auth(message.chat.id, message.from_user.id, "edit", is_auth)
            if is_auth:
                return
        lang = await db.get_group_language(message.chat.id)
        username_or_name = (
            f"@{message.from_user.username}"
            if message.from_user.username
            else message.from_user.first_name
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🚨 ʀᴇᴘᴏʀᴛ sᴘᴀᴍ", url=SUPPORT_CHAT)
        ]])
        warning_msg = await message.reply_text(
            get_lang("edit_warning", lang, user=username_or_name, delay=delay),
            reply_markup=keyboard
        )
        await asyncio.sleep(delay * 60)
        try:
            await message.delete()
            await warning_msg.delete()
        except:
            pass
    except Exception as e:
        logger.error(f"Error handling edited message: {e}")

@Client.on_message(filters.command(["auth", "eauth"]) & filters.group)
@admin_only
async def edit_auth(client: Client, message: Message):
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
        await message.reply_text(get_lang("eauth_usage", lang))
        return
    await db.add_edit_auth(message.chat.id, user_id)
    cache.set_auth(message.chat.id, user_id, "edit", True)
    await db.log_admin_action(message.chat.id, message.from_user.id, "edit_auth", user_id)
    await message.reply_text(get_lang("eauth_success", lang))

@Client.on_message(filters.command(["unauth", "eunauth"]) & filters.group)
@admin_only
async def edit_unauth(client: Client, message: Message):
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
        await message.reply_text(get_lang("eunauth_usage", lang))
        return
    await db.remove_edit_auth(message.chat.id, user_id)
    cache.set_auth(message.chat.id, user_id, "edit", False)
    await message.reply_text(get_lang("eunauth_success", lang))

@Client.on_message(filters.command(["authlist", "eauthlist"]) & filters.group)
async def edit_auth_list(client: Client, message: Message):
    lang = await db.get_group_language(message.chat.id)
    auth_users = await db.get_edit_auth_list(message.chat.id)
    if not auth_users:
        await message.reply_text(get_lang("no_auth_users", lang))
        return
    text = get_lang("eauthlist_header", lang) + "\n\n"
    for idx, user in enumerate(auth_users, 1):
        text += f"{idx}. User ID: `{user['user_id']}`\n"
    await message.reply_text(text)
