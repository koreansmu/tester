from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from utils.helpers import get_lang
from utils.database import Database
from config import BOT_USERNAME, SUPPORT_CHANNEL

db = Database()

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    user = message.from_user
    await db.add_user(user.id, user.username, user.first_name)
    lang = await db.get_user_language(user.id) or "en"

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "➕ ᴀᴅᴅ ᴍᴇ",
                    url=f"https://t.me/{BOT_USERNAME}?startgroup=true"
                )
            ],
            [
                InlineKeyboardButton("📢 ʙᴏᴛ ɴᴇᴡs", url=f"{SUPPORT_CHANNEL}"),
                InlineKeyboardButton("🌐 ʟᴀɴɢᴜᴀɢᴇ", callback_data="lang_menu"),
            ],
            [InlineKeyboardButton("❓ ʜᴇʟᴘ", callback_data="help_menu")],
        ]
    )

    start_text = get_lang("start_message", lang, mention=user.mention)
    await message.reply_text(start_text, reply_markup=keyboard, disable_web_page_preview=True)


@Client.on_message(filters.command("start") & filters.group)
async def start_group(client: Client, message: Message):
    lang = await db.get_group_language(message.chat.id) or "en"
    await db.add_active_group(message.chat.id, message.chat.title)

    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("❓ ʜᴇʟᴘ", callback_data="help_menu")],
            [InlineKeyboardButton("🌐 ʟᴀɴɢᴜᴀɢᴇ", callback_data="lang_menu")],
        ]
    )

    txt = get_lang("group_start", lang)
    await message.reply_text(txt, reply_markup=keyboard)
