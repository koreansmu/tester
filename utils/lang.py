from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
import logging
from utils.helpers import get_lang
from utils.cache import get_cache, init_cache

logger = logging.getLogger(__name__)

LANGUAGES = {
    "en": "🇬🇧 English",
    "hi": "🇮🇳 हिंदी"
}

def get_language_keyboard(current_lang: str = "en"):
    buttons = []
    for code, name in LANGUAGES.items():
        check = "✅ " if code == current_lang else ""
        buttons.append([InlineKeyboardButton(f"{check}{name}", callback_data=f"lang_{code}")])
    buttons.append([InlineKeyboardButton("❌ Close", callback_data="lang_close")])
    return InlineKeyboardMarkup(buttons)

async def _ensure_cache():
    try:
        return get_cache()
    except Exception:
        try:
            from utils.database import Database
            db = Database()
            try:
                cache = await init_cache(db=db, use_db_once=False)
                return cache
            except Exception as e:
                logger.warning("init_cache failed: %s. Falling back to in-memory cache.", e)
        except Exception as e:
            logger.warning("Could not import Database for cache init: %s", e)
        class _FallbackCache:
            def get_setting(self, key, setting=None):
                return None
            def set_setting(self, key, setting, value):
                return None
        return _FallbackCache()

async def _get_user_lang(user_id: int) -> str:
    cache = await _ensure_cache()
    try:
        lang = await asyncio.to_thread(lambda: cache.get_setting(user_id, "language"))
    except Exception:
        lang = None
    if lang:
        return lang
    from utils.database import Database
    db = Database()
    try:
        lang = await db.get_user_language(user_id) or "en"
    except Exception:
        lang = "en"
    try:
        await asyncio.to_thread(lambda: cache.set_setting(user_id, "language", lang))
    except Exception:
        pass
    return lang

async def _get_group_lang(chat_id: int) -> str:
    cache = await _ensure_cache()
    try:
        lang = await asyncio.to_thread(lambda: cache.get_setting(chat_id, "language"))
    except Exception:
        lang = None
    if lang:
        return lang
    from utils.database import Database
    db = Database()
    try:
        lang = await db.get_group_language(chat_id) or "en"
    except Exception:
        lang = "en"
    try:
        await asyncio.to_thread(lambda: cache.set_setting(chat_id, "language", lang))
    except Exception:
        pass
    return lang

@Client.on_message(filters.command("lang"))
async def change_language_command(client: Client, message: Message):
    logger.debug("Received /lang from %s in chat %s", getattr(message.from_user, "id", None), getattr(message.chat, "id", None))
    chat = getattr(message, "chat", None)
    if chat is None or chat.type == "private":
        current_lang = await _get_user_lang(message.from_user.id)
        text = get_lang("lang_select_user", current_lang)
        keyboard = get_language_keyboard(current_lang)
        await message.reply_text(text, reply_markup=keyboard)
        return
    member = await client.get_chat_member(message.chat.id, message.from_user.id)
    status = (getattr(member, "status", "") or "").lower()
    if status not in ("creator", "administrator"):
        lang = await _get_group_lang(message.chat.id)
        await message.reply_text(get_lang("admin_only", lang))
        return
    current_lang = await _get_group_lang(message.chat.id)
    text = get_lang("lang_select_group", current_lang)
    keyboard = get_language_keyboard(current_lang)
    await message.reply_text(text, reply_markup=keyboard)

@Client.on_callback_query(filters.regex("^lang_"))
async def language_callback(client: Client, callback: CallbackQuery):
    logger.debug("language_callback data=%s from=%s", callback.data, getattr(callback.from_user, "id", None))
    parts = callback.data.split("_", 1)
    if len(parts) < 2:
        await callback.answer()
        return
    data = parts[1]
    if data == "close":
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.answer()
        return
    msg = callback.message
    chat = getattr(msg, "chat", None)
    if chat is None or chat.type == "private":
        old_lang = await _get_user_lang(callback.from_user.id)
        if data == old_lang:
            keyboard = get_language_keyboard(old_lang)
            await callback.answer("Already selected.", show_alert=False)
            try:
                await callback.message.edit_text(get_lang("lang_changed_user", old_lang), reply_markup=keyboard)
            except Exception:
                pass
            return
        try:
            cache = get_cache()
            await asyncio.to_thread(lambda: cache.set_setting(callback.from_user.id, "language", data))
        except Exception:
            pass
        from utils.database import Database
        db = Database()
        asyncio.create_task(db.set_user_language(callback.from_user.id, data))
        text = get_lang("lang_changed_user", data)
        keyboard = get_language_keyboard(data)
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
            await callback.answer(f"Language changed to {LANGUAGES.get(data, data)}")
        except Exception:
            await callback.message.reply_text(text, reply_markup=keyboard)
            await callback.answer("Language updated!")
        return
    member = await client.get_chat_member(msg.chat.id, callback.from_user.id)
    status = (getattr(member, "status", "") or "").lower()
    if status not in ("creator", "administrator"):
        await callback.answer("You need to be an admin!", show_alert=True)
        return
    old_lang = await _get_group_lang(msg.chat.id)
    if data == old_lang:
        keyboard = get_language_keyboard(old_lang)
        await callback.answer("Already selected.", show_alert=False)
        try:
            await callback.message.edit_text(get_lang("lang_changed_group", old_lang), reply_markup=keyboard)
        except Exception:
            pass
        return
    try:
        cache = get_cache()
        await asyncio.to_thread(lambda: cache.set_setting(msg.chat.id, "language", data))
    except Exception:
        pass
    from utils.database import Database
    db = Database()
    asyncio.create_task(db.set_group_language(msg.chat.id, data))
    text = get_lang("lang_changed_group", data)
    keyboard = get_language_keyboard(data)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer(f"Language changed to {LANGUAGES.get(data, data)}")
    except Exception:
        await callback.message.reply_text(text, reply_markup=keyboard)
        await callback.answer("Language updated!")
