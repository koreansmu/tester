from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from utils.database import Database
from utils.helpers import get_lang
import logging

db = Database()
logger = logging.getLogger(__name__)

# Available languages
LANGUAGES = {
    "en": "🇬🇧 English",
    "hi": "hi": "🇮🇳 हिंदी (Hindi)"
}

def get_language_keyboard(current_lang: str = "en"):
    """Generate language selection keyboard"""
    buttons = []
    for code, name in LANGUAGES.items():
        check = "✅ " if code == current_lang else ""
        buttons.append([InlineKeyboardButton(f"{check}{name}", callback_data=f"lang_{code}")])
    
    buttons.append([InlineKeyboardButton("❌ Close", callback_data="lang_close")])
    return InlineKeyboardMarkup(buttons)

@Client.on_message(filters.command("lang"))
async def change_language(client: Client, Message):
    """Change language for user or group"""
    # Get current language
    if message.chat.type == "private":
        current_lang = await db.get_user_language(message.from_user.id)
        text = get_lang("lang_select_user", current_lang)
    else:
        # Check if user is admin
        try:
            member = await client.get_chat_member(message.chat.id, message.from_user.id)
            if member.status not in ["creator", "administrator"]:
                lang = await db.get_group_language(message.chat.id)
                await message.reply_text(get_lang("admin_only", lang))
                return
        except:
            return
        
        current_lang = await db.get_group_language(message.chat.id)
        text = get_lang("lang_select_group", current_lang)
    
    keyboard = get_language_keyboard(current_lang)
    await message.reply_text(text, reply_markup=keyboard)

@Client.on_callback_query(filters.regex("^lang_"))
async def language_callback(client: Client, callback: CallbackQuery):
    """Handle language selection callbacks"""
    data = callback.data.split("_")[1]
    
    if data == "close":
        await callback.message.delete()
        return
    
    # Set language
    if callback.message.chat.type == "private":
        await db.set_user_language(callback.from_user.id, data)
        text = get_lang("lang_changed_user", data)
    else:
        # Verify admin
        try:
            member = await client.get_chat_member(callback.message.chat.id, callback.from_user.id)
            if member.status not in ["creator", "administrator"]:
                await callback.answer("You need to be an admin!", show_alert=True)
                return
        except:
            return
        
        await db.set_group_language(callback.message.chat.id, data)
        text = get_lang("lang_changed_group", data)
    
    # Update keyboard
    keyboard = get_language_keyboard(data)
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer(f"Language changed to {LANGUAGES[data]}")
    except:
        await callback.answer("Language updated!", show_alert=False)
