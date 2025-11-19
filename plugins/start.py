import os
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
from utils.helpers import get_lang
from utils.database import Database
from config import BOT_USERNAME, SUPPORT_CHANNEL

db = Database()

def _normalize_channel_url(value: str) -> str | None:
    if not value:
        return None
    v = value.strip()
    if v.startswith("http://") or v.startswith("https://"):
        return v.replace(" ", "")
    v = v.lstrip("@")
    if v:
        return f"https://t.me/{v}"
    return None

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    user = message.from_user
    try:
        asyncio.create_task(db.add_user(user.id, user.username or "", user.first_name or ""))
    except Exception:
        pass
    lang = await db.get_user_language(user.id) or "en"
    add_me_url = f"https://t.me/{BOT_USERNAME.lstrip('@')}?startgroup=true"
    news_url = _normalize_channel_url(SUPPORT_CHANNEL)
    keyboard_rows = [
        [InlineKeyboardButton("➕ ᴀᴅᴅ ᴍᴇ", url=add_me_url)],
        [
            InlineKeyboardButton("🌐 ʟᴀɴɢᴜᴀɢᴇ", callback_data="lang_menu"),
            InlineKeyboardButton("❓ ʜᴇʟᴘ", callback_data="help_menu"),
        ],
    ]
    if news_url:
        keyboard_rows[1].insert(0, InlineKeyboardButton("📢 ʙᴏᴛ ɴᴇᴡs", url=news_url))
    keyboard = InlineKeyboardMarkup(keyboard_rows)
    txt = get_lang("start_message", lang, mention=user.mention)
    await message.reply_text(txt, reply_markup=keyboard, disable_web_page_preview=True)

@Client.on_message(filters.command("start") & filters.group)
async def start_group(client: Client, message: Message):
    try:
        asyncio.create_task(db.add_active_group(message.chat.id, message.chat.title or ""))
    except Exception:
        pass
    lang = await db.get_group_language(message.chat.id) or "en"
    keyboard = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("❓ ʜᴇʟᴘ", callback_data="help_menu")],
            [InlineKeyboardButton("🌐 ʟᴀɴɢᴜᴀɴᴇ", callback_data="lang_menu")],
        ]
    )
    txt = get_lang("group_start", lang)
    await message.reply_text(txt, reply_markup=keyboard, disable_web_page_preview=True)
