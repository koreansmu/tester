from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import logging
import time
from utils.decorators import admin_only
from utils.helpers import get_lang
from utils.database import Database
from utils.cache import CacheManager, get_cache
from config import SUPPORT_CHAT, LOGGER_ID

db = Database()
_cache_fallback = CacheManager()
logger = logging.getLogger(__name__)

_warned_users = {}
_media_events = {}
_bot_perms_cache = {}

WARN_COOLDOWN = 60
RATE_WINDOW = 10
RATE_THRESHOLD = 6
BOT_PERMS_CACHE_TTL = 300

def _get_cache():
    try:
        return get_cache()
    except Exception:
        return _cache_fallback

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

def _record_media_event(chat_id: int) -> int:
    now = time.time()
    events = _media_events.setdefault(chat_id, [])
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
        cache = _get_cache()
        try:
            await asyncio.to_thread(cache.set_setting, message.chat.id, "media_delay", delay)
        except TypeError:
            maybe = cache.set_setting(message.chat.id, "media_delay", delay)
            if asyncio.iscoroutine(maybe):
                await maybe
        if LOGGER_ID:
            try:
                admin_name = message.from_user.first_name or str(message.from_user.id)
                admin_username = f"@{message.from_user.username}" if message.from_user.username else admin_name
                log_msg = (
                    "⚙️ **Media Guard Updated**\n\n"
                    f"👤 Admin: {admin_name} ({admin_username})\n"
                    f"💬 Group: {message.chat.title}\n"
                    f"⏱ Delay: {delay} minute(s)"
                )
                await client.send_message(LOGGER_ID, log_msg)
            except Exception:
                pass
        await message.reply_text(get_lang("setdelay_success", lang, delay=delay))
    except ValueError:
        await message.reply_text(get_lang("invalid_number", lang))
    except Exception:
        await message.reply_text(get_lang("error_occurred", lang))

@Client.on_message(filters.command("getdelay") & filters.group)
async def get_media_delay(client: Client, message: Message):
    lang = await db.get_group_language(message.chat.id)
    cache = _get_cache()
    delay = None
    try:
        delay = cache.get_setting(message.chat.id, "media_delay")
    except Exception:
        delay = None
    if delay is None:
        delay = await db.get_media_delay(message.chat.id)
        if delay is not None:
            try:
                await asyncio.to_thread(cache.set_setting, message.chat.id, "media_delay", delay)
            except TypeError:
                maybe = cache.set_setting(message.chat.id, "media_delay", delay)
                if asyncio.iscoroutine(maybe):
                    await maybe
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
        user = message.from_user
        if not user:
            return

        cache = _get_cache()

        is_gbanned = None
        try:
            is_gbanned = cache.get_gban(user.id)
        except Exception:
            is_gbanned = None
        if is_gbanned is None:
            try:
                is_gbanned = await db.is_gbanned(user.id)
            except Exception:
                is_gbanned = False
            try:
                await asyncio.to_thread(cache.set_gban, user.id, is_gbanned)
            except TypeError:
                maybe = cache.set_gban(user.id, is_gbanned)
                if asyncio.iscoroutine(maybe):
                    await maybe
        if is_gbanned:
            try:
                await message.delete()
            except Exception:
                pass
            return

        delay = None
        try:
            delay = cache.get_setting(message.chat.id, "media_delay")
        except Exception:
            delay = None
        if delay is None:
            delay = await db.get_media_delay(message.chat.id)
            if delay is not None:
                try:
                    await asyncio.to_thread(cache.set_setting, message.chat.id, "media_delay", delay)
                except TypeError:
                    maybe = cache.set_setting(message.chat.id, "media_delay", delay)
                    if asyncio.iscoroutine(maybe):
                        await maybe
        if not delay:
            return

        can_send, can_delete = await _get_bot_perms(client, message.chat.id)
        if not can_send:
            return

        user_is_admin = False
        try:
            member = await client.get_chat_member(message.chat.id, user.id)
            status = (getattr(member, "status", "") or "").lower()
            user_is_admin = status in ("creator", "administrator")
        except Exception:
            user_is_admin = False

        if user_is_admin:
            is_auth = None
            try:
                is_auth = cache.get_auth(message.chat.id, user.id, "media")
            except Exception:
                is_auth = None
            if is_auth is None:
                try:
                    is_auth = await db.is_media_authorized(message.chat.id, user.id)
                except Exception:
                    is_auth = False
                try:
                    await asyncio.to_thread(cache.set_auth, message.chat.id, user.id, "media", is_auth)
                except TypeError:
                    maybe = cache.set_auth(message.chat.id, user.id, "media", is_auth)
                    if asyncio.iscoroutine(maybe):
                        await maybe
            if is_auth:
                return

        recent = _record_media_event(message.chat.id)
        if recent > RATE_THRESHOLD:
            return

        if _was_warned_recently(message.chat.id, user.id):
            return

        lang = await db.get_group_language(message.chat.id)
        username = f"@{user.username}" if getattr(user, "username", None) else (user.first_name or str(user.id))
        warning_text = get_lang("media_warning", lang, user=username, delay=delay)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🚨 ʀᴇᴘᴏʀᴛ sᴘᴀᴍ", url=SUPPORT_CHAT)]])

        try:
            warning_msg = await message.reply_text(warning_text, reply_markup=keyboard)
        except Exception:
            try:
                warning_msg = await client.send_message(message.chat.id, warning_text, reply_markup=keyboard)
            except Exception:
                return

        _mark_warned(message.chat.id, user.id)

        async def _del_after_delay(msg: Message, warn_msg: Message, chat: int, uid: int, can_del: bool, mins: int):
            await asyncio.sleep(mins * 60)
            try:
                is_admin_now = False
                try:
                    member = await client.get_chat_member(chat, uid)
                    status = (getattr(member, "status", "") or "").lower()
                    is_admin_now = status in ("creator", "administrator")
                except Exception:
                    is_admin_now = False
                if is_admin_now:
                    is_auth2 = None
                    try:
                        is_auth2 = cache.get_auth(chat, uid, "media")
                    except Exception:
                        is_auth2 = None
                    if is_auth2 is None:
                        try:
                            is_auth2 = await db.is_media_authorized(chat, uid)
                        except Exception:
                            is_auth2 = False
                        try:
                            await asyncio.to_thread(cache.set_auth, chat, uid, "media", is_auth2)
                        except TypeError:
                            maybe = cache.set_auth(chat, uid, "media", is_auth2)
                            if asyncio.iscoroutine(maybe):
                                await maybe
                    if is_auth2:
                        if warn_msg and can_del:
                            try:
                                await warn_msg.delete()
                            except Exception:
                                pass
                        return
                if can_del:
                    try:
                        await msg.delete()
                    except Exception:
                        pass
                try:
                    await warn_msg.delete()
                except Exception:
                    pass
            except Exception:
                pass

        asyncio.create_task(_del_after_delay(message, warning_msg, message.chat.id, user.id, can_delete, int(delay)))

    except Exception as e:
        logger.error("Error handling media: %s", e, exc_info=True)

@Client.on_message(filters.command("mauth") & filters.group)
@admin_only
async def media_auth(client: Client, message: Message):
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
        await message.reply_text(get_lang("mauth_usage", lang))
        return
    await db.add_media_auth(message.chat.id, user_id)
    cache = _get_cache()
    try:
        await asyncio.to_thread(cache.set_auth, message.chat.id, user_id, "media", True)
    except TypeError:
        maybe = cache.set_auth(message.chat.id, user_id, "media", True)
        if asyncio.iscoroutine(maybe):
            await maybe
    try:
        await db.log_admin_action(message.chat.id, message.from_user.id, "media_auth", user_id)
    except Exception:
        pass
    await message.reply_text(get_lang("mauth_success", lang))

@Client.on_message(filters.command("munauth") & filters.group)
@admin_only
async def media_unauth(client: Client, message: Message):
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
        await message.reply_text(get_lang("munauth_usage", lang))
        return
    await db.remove_media_auth(message.chat.id, user_id)
    cache = _get_cache()
    try:
        await asyncio.to_thread(cache.set_auth, message.chat.id, user_id, "media", False)
    except TypeError:
        maybe = cache.set_auth(message.chat.id, user_id, "media", False)
        if asyncio.iscoroutine(maybe):
            await maybe
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
        uid = user.get("user_id") if isinstance(user, dict) else user
        text += f"{idx}. User ID: `{uid}`\n"
    await message.reply_text(text)
