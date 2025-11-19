import os
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from utils.helpers import get_lang
from utils.database import Database

db = Database()

def get_help_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📸 ᴍᴇᴅɪᴀ ɢᴜᴀʀᴅ", callback_data="help_media"),
            InlineKeyboardButton("✏️ ᴇᴅɪᴛ ɢᴜᴀʀᴅ", callback_data="help_edit")
        ],
        [
            InlineKeyboardButton("🚫 sʟᴀɴɢ ғɪʟᴛᴇʀ", callback_data="help_slang"),
            InlineKeyboardButton("👤 ᴘʀᴇᴛᴇɴᴅᴇʀ", callback_data="help_pretender")
        ],
        [
            InlineKeyboardButton("⚙️ ᴀᴅᴍɪɴ ᴄᴍᴅs", callback_data="help_admin"),
            InlineKeyboardButton("ᴏᴡɴᴇʀ ᴄᴍᴅs ®", callback_data="help_owner")
        ],
        [
            InlineKeyboardButton("🏠 ʙᴀᴄᴋ", callback_data="help_back")
        ]
    ])

@Client.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    if message.chat.type in ("group", "supergroup"):
        lang = await db.get_group_language(message.chat.id) or "en"
    else:
        lang = await db.get_user_language(message.from_user.id) or "en"
    help_text = get_lang("help_main", lang)
    await message.reply_text(help_text, reply_markup=get_help_keyboard(), disable_web_page_preview=True)

@Client.on_callback_query(filters.regex("^help_"))
async def help_callback(client: Client, callback: CallbackQuery):
    data = callback.data
    if callback.message and callback.message.chat and callback.message.chat.type in ("group", "supergroup"):
        lang = await db.get_group_language(callback.message.chat.id) or "en"
    else:
        lang = await db.get_user_language(callback.from_user.id) or "en"

    if data == "help_menu":
        text = get_lang("help_main", lang)
        keyboard = get_help_keyboard()
    elif data == "help_media":
        text = get_lang("help_media_guard", lang)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("< ʙᴀᴄᴋ", callback_data="help_menu")]])
    elif data == "help_edit":
        text = get_lang("help_edit_guard", lang)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("< ʙᴀᴄᴋ", callback_data="help_menu")]])
    elif data == "help_slang":
        text = get_lang("help_slang_filter", lang)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("< ʙᴀᴄᴋ", callback_data="help_menu")]])
    elif data == "help_pretender":
        text = get_lang("help_pretender_detect", lang)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("< ʙᴀᴄᴋ", callback_data="help_menu")]])
    elif data == "help_admin":
        text = get_lang("help_admin_cmds", lang)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("< ʙᴀᴄᴋ", callback_data="help_menu")]])
    elif data == "help_owner":
        text = get_lang("help_owner_cmds", lang)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("< ʙᴀᴄᴋ", callback_data="help_menu")]])
    elif data == "help_back":
        text = get_lang("start_message", lang, mention=callback.from_user.mention)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("ʜᴇʟᴘ </>", callback_data="help_menu")]])
    else:
        await callback.answer()
        return

    try:
        if callback.message:
            await callback.message.edit_text(text, reply_markup=keyboard)
            await callback.answer()
        else:
            await client.send_message(callback.from_user.id, text, reply_markup=keyboard)
            await callback.answer()
    except Exception:
        await callback.answer("No changes.", show_alert=False)
