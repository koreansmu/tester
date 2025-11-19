from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    LinkPreviewOptions
)
import asyncio
from utils.helpers import get_lang
from utils.cache import get_cache

def get_help_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📸 ᴍᴇᴅɪᴀ ɢᴜᴀʀᴅ", callback_data="help_media"),
            InlineKeyboardButton("✏️ ᴇᴅɪᴛ ɢᴜᴀʀᴅ", callback_data="help_edit"),
        ],
        [
            InlineKeyboardButton("🚫 sʟᴀɴɢ ғɪʟᴛᴇʀ", callback_data="help_slang"),
            InlineKeyboardButton("👤 ᴘʀᴇᴛᴇɴᴅᴇʀ", callback_data="help_pretender"),
        ],
        [
            InlineKeyboardButton("⚙️ ᴀᴅᴍɪɴ ᴄᴍᴅs", callback_data="help_admin"),
            InlineKeyboardButton("ᴏᴡɴᴇʀ ᴄᴍᴅs ®", callback_data="help_owner"),
        ],
        [InlineKeyboardButton("🏠 ʙᴀᴄᴋ", callback_data="help_back")]
    ])

@Client.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    cache = get_cache() if get_cache else None

    if message.chat.type in ("group", "supergroup"):
        lang = await asyncio.to_thread(lambda: cache.get_setting(message.chat.id, "language")) if cache else None
    else:
        lang = await asyncio.to_thread(lambda: cache.get_setting(message.from_user.id, "language")) if cache else None
    lang = lang or "en"

    txt = get_lang("help_main", lang)

    await message.reply_text(
        txt,
        reply_markup=get_help_keyboard(),
        link_preview_options=LinkPreviewOptions(is_disabled=True)
    )

@Client.on_callback_query(filters.regex("^help_"))
async def help_callback(client: Client, callback: CallbackQuery):
    cache = get_cache() if get_cache else None

    if callback.message and callback.message.chat.type in ("group", "supergroup"):
        lang = await asyncio.to_thread(lambda: cache.get_setting(callback.message.chat.id, "language")) if cache else None
    else:
        lang = await asyncio.to_thread(lambda: cache.get_setting(callback.from_user.id, "language")) if cache else None
    lang = lang or "en"

    d = callback.data

    if d == "help_menu":
        txt = get_lang("help_main", lang)
        kb = get_help_keyboard()
    elif d == "help_media":
        txt = get_lang("help_media_guard", lang)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("< ʙᴀᴄᴋ", callback_data="help_menu")]])
    elif d == "help_edit":
        txt = get_lang("help_edit_guard", lang)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("< ʙᴀᴄᴋ", callback_data="help_menu")]])
    elif d == "help_slang":
        txt = get_lang("help_slang_filter", lang)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("< ʙᴀᴄᴋ", callback_data="help_menu")]])
    elif d == "help_pretender":
        txt = get_lang("help_pretender_detect", lang)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("< ʙᴀᴄᴋ", callback_data="help_menu")]])
    elif d == "help_admin":
        txt = get_lang("help_admin_cmds", lang)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("< ʙᴀᴄᴋ", callback_data="help_menu")]])
    elif d == "help_owner":
        txt = get_lang("help_owner_cmds", lang)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("< ʙᴀᴄᴋ", callback_data="help_menu")]])
    elif d == "help_back":
        txt = get_lang("start_message", lang, mention=callback.from_user.mention)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("ʜᴇʟᴘ </>", callback_data="help_menu")]])
    else:
        await callback.answer()
        return

    await callback.message.edit_text(
        txt,
        reply_markup=kb,
        link_preview_options=LinkPreviewOptions(is_disabled=True)
    )
    await callback.answer()
