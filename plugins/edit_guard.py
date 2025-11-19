from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import logging
import time

from utils.decorators import admin_only
from utils.helpers import get_lang, is_admin
from utils.database import Database
from utils.cache import CacheManager
from config import SUPPORT_CHAT, LOGGER_ID

db = Database()
cache = CacheManager()
logger = logging.getLogger(__name__)

_warned_users = {}
_edit_events = {}
_bot_perms_cache = {}

WARN_COOLDOWN = 60
RATE_WINDOW = 10
RATE_THRESHOLD = 6
BOT_PERMS_CACHE_TTL = 300


async def _get_bot_perms(client: Client, chat_id: int) -> tuple[bool, bool]:
    now = time.time()
    cached = _bot_perms_cache.get(chat_id)
    if cached and cached[2] > now:
        return cached[0], cached[1]
    try:
        me = await client.get_me()
        bot_member = await client.get_chat_member(chat_id, me.id)
        status = getattr(bot_member, "status", "").lower()
        can_send = True
        can_delete = True
        if status in ("kicked", "left", ""):
            can_send = False
            can_delete = False
        else:
            if hasattr(bot_member, "can_send_messages"):
                can_send = bool(bot_member.can_send_messages)
            if hasattr(bot_member, "can_delete_messages"):
                can_delete = bool(bot_member.can_delete_messages)
        _bot_perms_cache[chat_id] = (can_send, can_delete, now + BOT_PERMS_CACHE_TTL)
        return can_send, can_delete
    except Exception:
        _bot_perms_cache[chat_id] = (False, False, now + BOT_PERMS_CACHE_TTL)
        return False, False


def _record_edit_event(chat_id: int) -> int:
    now = time.time()
    events = _edit_events.setdefault(chat_id, [])
    events.append(now)
    cutoff = now - RATE_WINDOW
    while events and events[0] < cutoff:
        events.pop(0)
    return len(events)


def _was_warned_recently(chat_id: int, user_id: int) -> bool:
    ts = _warned_users.get((chat_id, user_id))
    if not ts:
        return False
    if time.time() - ts < WARN_COOLDOWN:
        return True
    _warned_users.pop((chat_id, user_id), None)
    return False


def _mark_warned(chat_id: int, user_id: int) -> None:
    _warned_users[(chat_id, user_id)] = time.time()


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
            try:
                admin_name = message.from_user.first_name or str(message.from_user.id)
                admin_username = f"@{message.from_user.username}" if message.from_user.username else admin_name
                log_msg = (
                    "✏️ **Edit Guard Updated**\n\n"
                    f"👤 Admin: {admin_name} ({admin_username})\n"
                    f"💬 Group: {message.chat.title}\n"
                    f"⏱ Delay: {delay} minute(s)"
                )
                await client.send_message(LOGGER_ID, log_msg)
            except Exception:
                pass
        await message.reply_text(get_lang("edelay_success", lang, delay=delay))
    except ValueError:
        await message.reply_text(get_lang("invalid_number", lang))
    except Exception:
        await message.reply_text(get_lang("error_occurred", lang))


@Client.on_edited_message(filters.group)
async def handle_edited_message(client: Client, message: Message):
    try:
        chat_id = message.chat.id
        user = message.from_user
        if not user:
            return
        delay = cache.get_setting(chat_id, "edit_delay")
        if delay is None:
            delay = await db.get_edit_delay(chat_id)
            if delay is not None:
                cache.set_setting(chat_id, "edit_delay", delay)
        if not delay:
            return
        can_send, can_delete = await _get_bot_perms(client, chat_id)
        if not can_send:
            return
        user_is_admin = await is_admin(client, chat_id, user.id)
        if user_is_admin:
            is_auth = cache.get_auth(chat_id, user.id, "edit")
            if is_auth is None:
                is_auth = await db.is_edit_authorized(chat_id, user.id)
                cache.set_auth(chat_id, user.id, "edit", is_auth)
            if is_auth:
                return
        recent = _record_edit_event(chat_id)
        if recent > RATE_THRESHOLD:
            return
        if _was_warned_recently(chat_id, user.id):
            return
        lang = await db.get_group_language(chat_id)
        username = f"@{user.username}" if user.username else user.first_name
        warning_text = get_lang("edit_warning", lang, user=username, delay=delay)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🚨 ʀᴇᴘᴏʀᴛ sᴘᴀᴍ", url=SUPPORT_CHAT)]])
        try:
            warning_msg = await message.reply_text(warning_text, reply_markup=keyboard)
        except Exception:
            try:
                warning_msg = await client.send_message(chat_id, warning_text, reply_markup=keyboard)
            except Exception:
                return
        _mark_warned(chat_id, user.id)

        async def _delayed_delete(msg, warn, chat, uid, del_ok, mins):
            await asyncio.sleep(mins * 60)
            try:
                if await is_admin(client, chat, uid):
                    is_auth = cache.get_auth(chat, uid, "edit")
                    if is_auth is None:
                        is_auth = await db.is_edit_authorized(chat, uid)
                        cache.set_auth(chat, uid, "edit", is_auth)
                    if is_auth:
                        if warn and del_ok:
                            try:
                                await warn.delete()
                            except:
                                pass
                        return
                if del_ok:
                    try:
                        await msg.delete()
                    except:
                        pass
                try:
                    await warn.delete()
                except:
                    pass
            except Exception:
                pass

        asyncio.create_task(_delayed_delete(message, warning_msg, chat_id, user.id, can_delete, int(delay)))

    except Exception:
        pass


@Client.on_message(filters.command(["auth", "eauth"]) & filters.group)
@admin_only
async def edit_auth(client: Client, message: Message):
    lang = await db.get_group_language(message.chat.id)
    if message.reply_to_message and message.reply_to_message.from_user:
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
    try:
        await db.log_admin_action(message.chat.id, message.from_user.id, "edit_auth", user_id)
    except Exception:
        pass
    await message.reply_text(get_lang("eauth_success", lang))


@Client.on_message(filters.command(["unauth", "eunauth"]) & filters.group)
@admin_only
async def edit_unauth(client: Client, message: Message):
    lang = await db.get_group_language(message.chat.id)
    if message.reply_to_message and message.reply_to_message.from_user:
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
    users = await db.get_edit_auth_list(message.chat.id)
    if not users:
        await message.reply_text(get_lang("no_auth_users", lang))
        return
    text = get_lang("eauthlist_header", lang) + "\n\n"
    for idx, user in enumerate(users, 1):
        uid = user.get("user_id") if isinstance(user, dict) else user
        text += f"{idx}. User ID: `{uid}`\n"
    await message.reply_text(text)
