from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, LinkPreviewOptions
import asyncio
from utils.helpers import get_lang
from utils.cache import get_cache
from utils.database import Database
from config import BOT_USERNAME, SUPPORT_CHANNEL

db = Database()

def _normalize_channel_url(value: str) -> str | None:
    if not value:
        return None
    v = value.strip()
    if v.startswith(("http://", "https://")):
        return v.replace(" ", "")
    v = v.lstrip("@")
    return f"https://t.me/{v}" if v else None

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    user = message.from_user
    cache = get_cache() if get_cache else None

    saved = await asyncio.to_thread(lambda: cache.get_setting(user.id, "saved")) if cache else None

    if not saved:
        asyncio.create_task(db.add_user(user.id, user.username or "", user.first_name or ""))
        if cache:
            await asyncio.to_thread(lambda: cache.set_setting(user.id, "saved", True))

    lang = await asyncio.to_thread(lambda: cache.get_setting(user.id, "language")) if cache else None
    lang = lang or "en"

    add_me_url = f"https://t.me/{BOT_USERNAME.lstrip('@')}?startgroup=true"
    news_url = _normalize_channel_url(SUPPORT_CHANNEL)

    rows = [
        [InlineKeyboardButton("➕ ᴀᴅᴅ ᴍᴇ", url=add_me_url)],
        [
            InlineKeyboardButton("🌐 ʟᴀɴɢᴜᴀɢᴇ", callback_data="lang_menu"),
            InlineKeyboardButton("❓ ʜᴇʟᴘ", callback_data="help_menu"),
        ],
    ]

    if news_url:
        rows[1].insert(0, InlineKeyboardButton("📢 ʙᴏᴛ ɴᴇᴡs", url=news_url))

    kb = InlineKeyboardMarkup(rows)
    txt = get_lang("start_message", lang, mention=user.mention)

    await message.reply_text(
        txt,
        reply_markup=kb,
        link_preview_options=LinkPreviewOptions(is_disabled=True)
    )

@Client.on_message(filters.command("start") & filters.group)
async def start_group(client: Client, message: Message):
    cache = get_cache() if get_cache else None

    saved = await asyncio.to_thread(lambda: cache.get_setting(message.chat.id, "group_saved")) if cache else None

    if not saved:
        asyncio.create_task(db.add_active_group(message.chat.id, message.chat.title or ""))
        if cache:
            await asyncio.to_thread(lambda: cache.set_setting(message.chat.id, "group_saved", True))

    lang = await asyncio.to_thread(lambda: cache.get_setting(message.chat.id, "language")) if cache else None
    lang = lang or "en"

    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("❓ ʜᴇʟᴘ", callback_data="help_menu")],
            [InlineKeyboardButton("🌐 ʟᴀɴɢᴜᴀɢᴇ", callback_data="lang_menu")],
        ]
    )

    txt = get_lang("group_start", lang)

    await message.reply_text(
        txt,
        reply_markup=kb,
        link_preview_options=LinkPreviewOptions(is_disabled=True)
    )
