from functools import wraps
from pyrogram import Client
from pyrogram.types import Message
from utils.lang import get_lang
from utils.database import Database
import logging

db = Database()
logger = logging.getLogger(__name__)


async def _get_lang_for(message: Message):
    if message.chat and message.chat.type in ("group", "supergroup"):
        return await db.get_group_language(message.chat.id) or "en"
    return "en"


def owner_only(func):
    @wraps(func)
    async def wrapper(client: Client, message: Message):
        lang = await _get_lang_for(message)
        if message.from_user.id != client.me.id:
            await message.reply_text(
                get_lang("owner_only", lang)
            )
            return
        return await func(client, message)
    return wrapper


def sudo_only(func):
    @wraps(func)
    async def wrapper(client: Client, message: Message):
        lang = await _get_lang_for(message)
        uid = message.from_user.id
        sudo = client.sudo if hasattr(client, "sudo") else []
        owner = client.me.id

        if uid not in sudo and uid != owner:
            await message.reply_text(
                get_lang("sudo_only", lang)
            )
            return
        return await func(client, message)
    return wrapper


def admin_only(func):
    @wraps(func)
    async def wrapper(client: Client, message: Message):
        lang = await _get_lang_for(message)

        if message.chat.type == "private":
            await message.reply_text(
                get_lang("group_only", lang)
            )
            return

        try:
            member = await client.get_chat_member(message.chat.id, message.from_user.id)
            status = (member.status or "").lower()

            if status not in ("administrator", "creator"):
                await message.reply_text(
                    get_lang("admin_only", lang)
                )
                return
        except Exception as e:
            logger.error(f"admin check error: {e}")
            return

        return await func(client, message)
    return wrapper


def creator_only(func):
    @wraps(func)
    async def wrapper(client: Client, message: Message):
        lang = await _get_lang_for(message)

        if message.chat.type == "private":
            await message.reply_text(
                get_lang("group_only", lang)
            )
            return

        try:
            member = await client.get_chat_member(message.chat.id, message.from_user.id)
            status = (member.status or "").lower()

            if status != "creator":
                await message.reply_text(
                    get_lang("creator_only", lang)
                )
                return
        except Exception as e:
            logger.error(f"creator check error: {e}")
            return

        return await func(client, message)
    return wrapper
