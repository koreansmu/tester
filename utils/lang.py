from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
from utils.helpers import get_lang
from utils.cache import get_cache, init_cache
from utils.database import Database

db = Database()

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
        return await init_cache(db=None, use_db_once=False)

async def _get_user_lang(user_id: int) -> str:
    cache = await _ensure_cache()
    lang = await asyncio.to_thread(lambda: cache.get_setting(user_id, "language"))
    if lang:
        return lang
    try:
        lang = await db.get_user_language(user_id) or "en"
    except Exception:
        lang = "en"
    await asyncio.to_thread(lambda: cache.set_setting(user_id, "language", lang))
    return lang

async def _get_group_lang(chat_id: int) -> str:
    cache = await _ensure_cache()
    lang = await asyncio.to_thread(lambda: cache.get_setting(chat_id, "language"))
    if lang:
        return lang
    try:
        lang = await db.get_group_language(chat_id) or "en"
    except Exception:
        lang = "en"
    await asyncio.to_thread(lambda: cache.set_setting(chat_id, "language", lang))
    return lang

@Client.on_message(filters.command("lang"))
async def change_language_command(client: Client, message: Message):
    if message.chat.type == "private":
        current_lang = await _get_user_lang(message.from_user.id)
        text = get_lang("lang_select_user", current_lang)
        keyboard = get_language_keyboard(current_lang)
        await message.reply_text(text, reply_markup=keyboard)
        return

    member = await client.get_chat_member(message.chat.id, message.from_user.id)
    if member.status not in ["creator", "administrator"]:
        lang = await _get_group_lang(message.chat.id)
        await message.reply_text(get_lang("admin_only", lang))
        return

    current_lang = await _get_group_lang(message.chat.id)
    text = get_lang("lang_select_group", current_lang)
    keyboard = get_language_keyboard(current_lang)
    await message.reply_text(text, reply_markup=keyboard)

@Client.on_callback_query(filters.regex("^lang_menu$"))
async def open_language_menu(client: Client, callback: CallbackQuery):
    if callback.message.chat.type == "private":
        current_lang = await _get_user_lang(callback.from_user.id)
        text = get_lang("lang_select_user", current_lang)
        keyboard = get_language_keyboard(current_lang)
        await callback.message.reply_text(text, reply_markup=keyboard)
        await callback.answer()
        return

    member = await client.get_chat_member(callback.message.chat.id, callback.from_user.id)
    if member.status not in ["creator", "administrator"]:
        lang = await _get_group_lang(callback.message.chat.id)
        await callback.answer(get_lang("admin_only", lang), show_alert=True)
        return

    current_lang = await _get_group_lang(callback.message.chat.id)
    text = get_lang("lang_select_group", current_lang)
    keyboard = get_language_keyboard(current_lang)
    await callback.message.reply_text(text, reply_markup=keyboard)
    await callback.answer()

@Client.on_callback_query(filters.regex("^lang_"))
async def language_callback(client: Client, callback: CallbackQuery):
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

    if callback.message.chat.type == "private":
        old_lang = await _get_user_lang(callback.from_user.id)
        if data == old_lang:
            keyboard = get_language_keyboard(old_lang)
            await callback.answer("Already selected.", show_alert=False)
            try:
                await callback.message.edit_text(get_lang("lang_changed_user", old_lang), reply_markup=keyboard)
            except Exception:
                pass
            return
        await asyncio.to_thread(lambda: get_cache().set_setting(callback.from_user.id, "language", data))
        asyncio.create_task(db.set_user_language(callback.from_user.id, data))
        text = get_lang("lang_changed_user", data)
        keyboard = get_language_keyboard(data)
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
            await callback.answer(f"Language changed to {LANGUAGES[data]}")
        except Exception:
            await callback.message.reply_text(text, reply_markup=keyboard)
            await callback.answer("Language updated!")
        return

    member = await client.get_chat_member(callback.message.chat.id, callback.from_user.id)
    if member.status not in ["creator", "administrator"]:
        await callback.answer("You need to be an admin!", show_alert=True)
        return

    old_lang = await _get_group_lang(callback.message.chat.id)
    if data == old_lang:
        keyboard = get_language_keyboard(old_lang)
        await callback.answer("Already selected.", show_alert=False)
        try:
            await callback.message.edit_text(get_lang("lang_changed_group", old_lang), reply_markup=keyboard)
        except Exception:
            pass
        return

    await asyncio.to_thread(lambda: get_cache().set_setting(callback.message.chat.id, "language", data))
    asyncio.create_task(db.set_group_language(callback.message.chat.id, data))
    text = get_lang("lang_changed_group", data)
    keyboard = get_language_keyboard(data)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer(f"Language changed to {LANGUAGES[data]}")
    except Exception:
        await callback.message.reply_text(text, reply_markup=keyboard)
        await callback.answer("Language updated!")
