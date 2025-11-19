import os
import logging
from typing import Union, Dict
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConfigurationError
from pyrogram import Client, filters
from pyrogram.types import Message
from utils.decorators import creator_only
from utils.helpers import get_lang
from utils.database import Database
from utils.cache import CacheManager
import config

db = Database()
cache = CacheManager()
logger = logging.getLogger(__name__)

_motor_client = AsyncIOMotorClient(config.PRETENDER_DB_URI)

try:
    _default = _motor_client.get_default_database()
    if _default is None:
        raise ConfigurationError
    _impdb = _default.pretender
except ConfigurationError:
    _impdb = _motor_client[config.PRETENDER_DB_NAME].pretender

async def usr_data_in_imp(chat_id: int, user_id: int) -> bool:
    return bool(await _impdb.find_one({"chat_id": chat_id, "user_id": user_id}))

async def get_userdata_from_imp(chat_id: int, user_id: int) -> Union[Dict, None]:
    return await _impdb.find_one({"chat_id": chat_id, "user_id": user_id}, {"_id": 0})

async def add_userdata_to_imp(chat_id: int, user_id: int, username: Union[str, None], first_name: str, last_name: Union[str, None] = None):
    try:
        await _impdb.update_one(
            {"chat_id": chat_id, "user_id": user_id},
            {"$set": {"username": username, "first_name": first_name, "last_name": last_name}},
            upsert=True,
        )
    except Exception as e:
        logger.error(f"impdb update error {chat_id} {user_id}: {e}")

@Client.on_message(filters.command("pretender") & filters.group)
@creator_only
async def toggle_pretender(client: Client, message: Message):
    lang = await db.get_group_language(message.chat.id)
    if len(message.command) < 2:
        await message.reply_text(get_lang("pretender_usage", lang))
        return
    s = message.command[1].lower()
    if s == "on":
        await db.set_pretender(message.chat.id, True)
        cache.set_setting(message.chat.id, "pretender_enabled", True)
        await message.reply_text(get_lang("pretender_enabled", lang))
    elif s == "off":
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
    await message.reply_text(get_lang("spretender_on" if enabled else "spretender_off", lang))

@Client.on_message(filters.group & filters.text)
async def track_user_changes(client: Client, message: Message):
    try:
        enabled = cache.get_setting(message.chat.id, "pretender_enabled")
        if enabled is None:
            enabled = await db.get_pretender_status(message.chat.id)
            cache.set_setting(message.chat.id, "pretender_enabled", enabled)
        if not enabled:
            return

        u = message.from_user
        if not u:
            return

        key = f"{message.chat.id}:{u.id}"
        now = {"first_name": u.first_name or "", "username": u.username or None}
        old = cache.get_setting(key)

        if old is None:
            try:
                if hasattr(db, "get_pretender_user"):
                    res = await db.get_pretender_user(message.chat.id, u.id)
                elif hasattr(db, "get_userdata"):
                    res = await db.get_userdata(message.chat.id, u.id)
                else:
                    res = await get_userdata_from_imp(message.chat.id, u.id)
                if res:
                    old = {"first_name": res.get("first_name", ""), "username": res.get("username")}
                else:
                    old = None
            except Exception:
                old = None

        if old:
            lang = await db.get_group_language(message.chat.id)
            changes = []
            if old.get("first_name", "") != now["first_name"]:
                changes.append(get_lang("name_changed", lang, old=old.get("first_name") or "None", new=now["first_name"] or "None"))
            if old.get("username") != now["username"]:
                changes.append(
                    get_lang(
                        "username_changed",
                        lang,
                        old=old.get("username") or "None",
                        new=now["username"] or "None",
                    )
                )
            if changes:
                n = f"@{u.username}" if u.username else u.first_name or str(u.id)
                txt = get_lang("pretender_alert", lang, user=n) + "\n\n" + "\n".join(changes)
                await message.reply_text(txt, disable_web_page_preview=True)

        cache.set_setting(key, now.copy())
        await add_userdata_to_imp(message.chat.id, u.id, u.username, u.first_name, getattr(u, "last_name", None))

        if hasattr(db, "add_pretender_userdata"):
            await db.add_pretender_userdata(message.chat.id, u.id, u.username, u.first_name, getattr(u, "last_name", None))

    except Exception as e:
        logger.error(f"pretender error: {e}")
