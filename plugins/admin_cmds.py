from pyrogram import Client, filters
from pyrogram.types import Message, LinkPreviewOptions
import asyncio
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

def _is_sudo(uid: int) -> bool:
    if isinstance(SUDO_USERS, (list, tuple, set)):
        return uid in SUDO_USERS
    return uid == SUDO_USERS

async def _send(message: Message, text: str, reply_markup=None):
    try:
        await message.reply_text(text, reply_markup=reply_markup, link_preview_options=LinkPreviewOptions(is_disabled=True))
        return
    except TypeError:
        pass
    try:
        await message.reply_text(text, reply_markup=reply_markup, disable_web_page_preview=True)
        return
    except TypeError:
        pass
    await message.reply_text(text, reply_markup=reply_markup)

@Client.on_message(filters.command("reload") & filters.group)
@admin_only
async def reload_admins(client: Client, message: Message):
    lang = await db.get_group_language(message.chat.id)
    try:
        try:
            await asyncio.to_thread(cache.clear_admins, message.chat.id)
        except TypeError:
            maybe = cache.clear_admins(message.chat.id)
            if asyncio.iscoroutine(maybe):
                await maybe

        admins = []
        async for member in client.get_chat_members(message.chat.id, filter="administrators"):
            try:
                admins.append(member.user.id)
            except Exception:
                pass

        try:
            await asyncio.to_thread(cache.set_admins, message.chat.id, admins)
        except TypeError:
            maybe = cache.set_admins(message.chat.id, admins)
            if asyncio.iscoroutine(maybe):
                await maybe

        try:
            await db.set_group_admins(message.chat.id, admins)
        except Exception:
            pass

        await _send(message, get_lang("reload_success", lang, count=len(admins)))
    except Exception as e:
        logger.exception(e)
        await _send(message, get_lang("reload_failed", lang))

@Client.on_message(filters.command("autoclean") & filters.group)
@admin_only
async def toggle_autoclean(client: Client, message: Message):
    lang = await db.get_group_language(message.chat.id)

    if len(message.command) < 2:
        await _send(message, get_lang("autoclean_usage", lang))
        return

    status = message.command[1].lower()

    try:
        if status == "on":
            await db.set_auto_clean(message.chat.id, True)
            try:
                await asyncio.to_thread(cache.set_setting, message.chat.id, "auto_clean", True)
            except TypeError:
                maybe = cache.set_setting(message.chat.id, "auto_clean", True)
                if asyncio.iscoroutine(maybe):
                    await maybe
            await _send(message, get_lang("autoclean_enabled", lang))
        elif status == "off":
            await db.set_auto_clean(message.chat.id, False)
            try:
                await asyncio.to_thread(cache.set_setting, message.chat.id, "auto_clean", False)
            except TypeError:
                maybe = cache.set_setting(message.chat.id, "auto_clean", False)
                if asyncio.iscoroutine(maybe):
                    await maybe
            await _send(message, get_lang("autoclean_disabled", lang))
        else:
            await _send(message, get_lang("autoclean_usage", lang))
    except Exception as e:
        logger.exception(e)
        await _send(message, get_lang("autoclean_failed", lang))

@Client.on_message(filters.command("stats") & (filters.private | filters.group))
async def show_stats(client: Client, message: Message):
    if not _is_sudo(message.from_user.id):
        return

    lang = "en"
    try:
        stats = await db.get_total_stats()

        text = ""
        text += get_lang("stats_header", lang) + "\n\n"
        text += get_lang("stats_groups", lang, count=stats.get("total_groups", 0)) + "\n"
        text += get_lang("stats_users", lang, count=stats.get("total_users", 0)) + "\n\n"
        text += get_lang("stats_edit_enabled", lang, count=stats.get("edit_enabled", 0)) + "\n"
        text += get_lang("stats_media_enabled", lang, count=stats.get("media_enabled", 0)) + "\n"
        text += get_lang("stats_slang_enabled", lang, count=stats.get("slang_enabled", 0))

        await _send(message, text)
    except Exception as e:
        logger.exception(e)
        await _send(message, "An error occurred while fetching stats.")

@Client.on_message(filters.command("dev"))
async def developer_info(client: Client, message: Message):
    try:
        lang = await db.get_group_language(message.chat.id)
    except Exception:
        lang = "en"

    try:
        dev_text = get_lang("developer_info", lang)
        await _send(message, dev_text)
    except Exception as e:
        logger.exception(e)

@Client.on_message(filters.command("logadmin") & filters.group)
async def log_admin_activity(client: Client, message: Message):
    lang = await db.get_group_language(message.chat.id)

    if not await is_creator(client, message.chat.id, message.from_user.id):
        await _send(message, get_lang("creator_only", lang))
        return

    try:
        logs = await db.get_admin_logs(message.chat.id, limit=20)
    except Exception:
        logs = None

    if not logs:
        await _send(message, get_lang("no_admin_logs", lang))
        return

    parts = [get_lang("admin_logs_header", lang), ""]
    for log in logs:
        ts = datetime.datetime.fromtimestamp(log.get("timestamp", 0)).strftime("%Y-%m-%d %H:%M:%S")
        parts.append(f"⏰ {ts}")
        parts.append(f"👤 Admin: `{log.get('admin_id', 'unknown')}`")
        parts.append(f"📝 Action: {log.get('action', 'unknown')}")
        if log.get("target_user"):
            parts.append(f"🎯 Target: `{log.get('target_user')}`")
        parts.append("─" * 20)

    text = "\n".join(parts)
    if len(text) > 4000:
        text = text[:3990] + "\n\n(…truncated)"

    await _send(message, text)
