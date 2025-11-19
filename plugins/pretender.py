import asyncio
import os
import logging
import config
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Union, Dict
from pyrogram import Client, filters
from pyrogram.types import Message
from utils.decorators import creator_only
from utils.helpers import get_lang
from utils.database import Database
from utils.cache import CacheManager


db = Database()
cache = CacheManager()
logger = logging.getLogger(__name__)

MONGO_DB_URI = config.PRETENDER_DB_URI

_motor_client = AsyncIOMotorClient(MONGO_DB_URI)
_impdb = _motor_client.get_default_database().pretender

async def usr_data_in_imp(chat_id: int, user_id: int) -> bool:
    r = await _impdb.find_one({"chat_id": chat_id, "user_id": user_id})
    return bool(r)

async def get_userdata_from_imp(chat_id: int, user_id: int) -> Union[Dict[str, str], None]:
    return await _impdb.find_one({"chat_id": chat_id, "user_id": user_id}, {"_id": 0})

async def add_userdata_to_imp(chat_id: int, user_id: int, username: Union[str, None], first_name: str, last_name: Union[str, None] = None):
    try:
        await _impdb.update_one(
            {"chat_id": chat_id, "user_id": user_id},
            {"$set": {"username": username, "first_name": first_name, "last_name": last_name}},
            upsert=True,
        )
    except Exception as e:
        logger.error(f"Failed to update impdb user data in {chat_id} for user {user_id}: {e}")
        try:
            if os.getenv("LOGGER_ID"):
                await Client.send_message(None, int(os.getenv("LOGGER_ID")), f"Failed to update pretender impdb: {e}")
        except Exception:
            pass

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

@Client.on_message(filters.group & filters.text)
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
        current_data = {"first_name": user.first_name or "", "username": user.username or None}
        old_data = cache.get_setting(cache_key)
        if old_data is None:
            try:
                if hasattr(db, "get_pretender_user"):
                    res = await db.get_pretender_user(message.chat.id, user.id)
                elif hasattr(db, "get_userdata"):
                    res = await db.get_userdata(message.chat.id, user.id)
                else:
                    res = await get_userdata_from_imp(message.chat.id, user.id)
                if res:
                    old_data = {"first_name": res.get("first_name", ""), "username": res.get("username")}
                else:
                    old_data = None
            except Exception:
                old_data = None
        if old_data:
            lang = await db.get_group_language(message.chat.id)
            changes = []
            if old_data.get("first_name", "") != current_data["first_name"]:
                changes.append(get_lang("name_changed", lang, old=old_data.get("first_name") or "None", new=current_data["first_name"] or "None"))
            if old_data.get("username") != current_data["username"]:
                old_un = old_data.get("username") or "None"
                new_un = current_data["username"] or "None"
                changes.append(get_lang("username_changed", lang, old=old_un, new=new_un))
            if changes:
                username_or_name = f"@{user.username}" if user.username else user.first_name or str(user.id)
                alert_text = get_lang("pretender_alert", lang, user=username_or_name)
                alert_text += "\n\n" + "\n".join(changes)
                await message.reply_text(alert_text, disable_web_page_preview=True)
        cache.set_setting(cache_key, current_data.copy())
        try:
            await add_userdata_to_imp(message.chat.id, user.id, user.username, user.first_name, getattr(user, "last_name", None))
        except Exception:
            pass
        try:
            if hasattr(db, "add_pretender_userdata"):
                await db.add_pretender_userdata(message.chat.id, user.id, user.username, user.first_name, getattr(user, "last_name", None))
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Error in pretender detection: {e}")
