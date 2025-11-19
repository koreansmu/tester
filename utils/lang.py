from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from utils.database import Database
from utils.helpers import get_lang

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

@Client.on_message(filters.command("lang"))
async def change_language_command(client: Client, message: Message):
    if message.chat.type == "private":
        current_lang = await db.get_user_language(message.from_user.id) or "en"
        text = get_lang("lang_select_user", current_lang)
    else:
        member = await client.get_chat_member(message.chat.id, message.from_user.id)
        if member.status not in ["creator", "administrator"]:
            lang = await db.get_group_language(message.chat.id) or "en"
            await message.reply_text(get_lang("admin_only", lang))
            return
        current_lang = await db.get_group_language(message.chat.id) or "en"
        text = get_lang("lang_select_group", current_lang)

    keyboard = get_language_keyboard(current_lang)
    await message.reply_text(text, reply_markup=keyboard)

@Client.on_callback_query(filters.regex("^lang_menu$"))
async def open_language_menu(client: Client, callback: CallbackQuery):
    if callback.message.chat.type == "private":
        current_lang = await db.get_user_language(callback.from_user.id) or "en"
        text = get_lang("lang_select_user", current_lang)
        keyboard = get_language_keyboard(current_lang)
        await callback.message.reply_text(text, reply_markup=keyboard)
        await callback.answer()
        return

    member = await client.get_chat_member(callback.message.chat.id, callback.from_user.id)
    if member.status not in ["creator", "administrator"]:
        lang = await db.get_group_language(callback.message.chat.id) or "en"
        await callback.answer(get_lang("admin_only", lang), show_alert=True)
        return

    current_lang = await db.get_group_language(callback.message.chat.id) or "en"
    text = get_lang("lang_select_group", current_lang)
    keyboard = get_language_keyboard(current_lang)
    await callback.message.reply_text(text, reply_markup=keyboard)
    await callback.answer()

@Client.on_callback_query(filters.regex("^lang_"))
async def language_callback(client: Client, callback: CallbackQuery):
    data = callback.data.split("_")[1]
    if data == "close":
        await callback.message.delete()
        await callback.answer()
        return

    if callback.message.chat.type == "private":
        await db.set_user_language(callback.from_user.id, data)
        text = get_lang("lang_changed_user", data)
    else:
        member = await client.get_chat_member(callback.message.chat.id, callback.from_user.id)
        if member.status not in ["creator", "administrator"]:
            await callback.answer("You need to be an admin!", show_alert=True)
            return
        await db.set_group_language(callback.message.chat.id, data)
        text = get_lang("lang_changed_group", data)

    keyboard = get_language_keyboard(data)

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer(f"Language changed to {LANGUAGES[data]}")
    except:
        await callback.message.reply_text(text, reply_markup=keyboard)
        await callback.answer("Language updated!")
