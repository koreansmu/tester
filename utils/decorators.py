from functools import wraps
from pyrogram import Client
from pyrogram.types import Message
from config import OWNER_ID, SUDO_USERS
import logging

logger = logging.getLogger(__name__)

def _extract_message(args, kwargs):
    for v in args:
        if isinstance(v, Message):
            return v
    for v in kwargs.values():
        if isinstance(v, Message):
            return v
    return None

def _extract_client(args, kwargs):
    if args:
        if isinstance(args[0], Client):
            return args[0]
    return kwargs.get("client")

def _is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID

def _is_sudo(user_id: int) -> bool:
    if isinstance(SUDO_USERS, (list, tuple, set)):
        return user_id in SUDO_USERS
    return user_id == SUDO_USERS

def _normalize_status(status) -> str:
    try:
        if status is None:
            return ""
        if isinstance(status, str):
            return status.lower()
        val = getattr(status, "value", None)
        if isinstance(val, str):
            return val.lower()
        s = str(status).lower()
        return s
    except Exception:
        return ""

async def _reply_with_lang(message: Message, key: str, lang: str = "en"):
    try:
        from utils.lang import get_lang
        text = await get_lang(key, lang)
    except Exception:
        text = key
    try:
        await message.reply_text(text)
    except Exception as e:
        logger.error(f"failed to send reply: {e}")

def owner_only(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        message = _extract_message(args, kwargs)
        if not message or not getattr(message, "from_user", None):
            return
        if not _is_owner(message.from_user.id):
            try:
                await _reply_with_lang(message, "owner_only", "en")
            except Exception:
                await message.reply_text("🛑 This command is only for my Owner!")
            return
        return await func(*args, **kwargs)
    return wrapper

def sudo_only(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        message = _extract_message(args, kwargs)
        if not message or not getattr(message, "from_user", None):
            return
        uid = message.from_user.id
        if not (_is_sudo(uid) or _is_owner(uid)):
            try:
                lang = "en"
                try:
                    from utils.database import Database
                    db = Database()
                    if message.chat and getattr(message.chat, "id", None):
                        lang = await db.get_group_language(message.chat.id) or "en"
                except Exception:
                    lang = "en"
                await _reply_with_lang(message, "sudo_only", lang)
            except Exception:
                await message.reply_text("🛑 This command requires superuser access!")
            return
        return await func(*args, **kwargs)
    return wrapper

def admin_only(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        message = _extract_message(args, kwargs)
        client = _extract_client(args, kwargs)
        if not message or not client:
            return
        if message.chat is None or getattr(message.chat, "type", "") == "private":
            try:
                await _reply_with_lang(message, "group_only", "en")
            except Exception:
                await message.reply_text("❌ This command is for groups only!")
            return
        try:
            member = await client.get_chat_member(message.chat.id, message.from_user.id)
            status = _normalize_status(getattr(member, "status", None))
            if not any(k in status for k in ("administrator", "creator", "owner", "admin")):
                try:
                    lang = "en"
                    try:
                        from utils.database import Database
                        db = Database()
                        lang = await db.get_group_language(message.chat.id) or "en"
                    except Exception:
                        lang = "en"
                    await _reply_with_lang(message, "admin_only", lang)
                except Exception:
                    await message.reply_text("🛑 This command is for admins only!")
                return
        except Exception as e:
            logger.error(f"admin_only check failed: {e}")
            return
        return await func(*args, **kwargs)
    return wrapper

def creator_only(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        message = _extract_message(args, kwargs)
        client = _extract_client(args, kwargs)
        if not message or not client:
            return
        if message.chat is None or getattr(message.chat, "type", "") == "private":
            try:
                await _reply_with_lang(message, "group_only", "en")
            except Exception:
                await message.reply_text("🛑 This command is for groups only!")
            return
        try:
            member = await client.get_chat_member(message.chat.id, message.from_user.id)
            status = _normalize_status(getattr(member, "status", None))
            if "creator" not in status and "owner" not in status:
                try:
                    lang = "en"
                    try:
                        from utils.database import Database
                        db = Database()
                        lang = await db.get_group_language(message.chat.id) or "en"
                    except Exception:
                        lang = "en"
                    await _reply_with_lang(message, "creator_only", lang)
                except Exception:
                    await message.reply_text("🛑 This command is restricted to group creator only!")
                return
        except Exception as e:
            logger.error(f"creator_only check failed: {e}")
            return
        return await func(*args, **kwargs)
    return wrapper
