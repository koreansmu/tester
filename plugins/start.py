from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from utils.helpers import get_lang
from utils.database import Database
from config import BOT_USERNAME, SUPPORT_CHAT, SUPPORT_CHANNEL

db = Database()

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    """Handle /start in private chats"""
    user = message.from_user

    # Save user to database (assuming db.add_user is async)
    await db.add_user(user.id, user.username, user.first_name)

    lang = await db.get_group_language(message.chat.id)

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "➕ ᴀᴅᴅ ᴍᴇ ",
                    url=f"https://t.me/{BOT_USERNAME}?startgroup=true",
                )
            ],
            [
                InlineKeyboardButton("📢 ʙᴏᴛ ɴᴇᴡs", url=f"https://t.me/{SUPPORT_CHANNEL}"),
                InlineKeyboardButton("💬 sᴜᴘᴘᴏʀᴛ", url=f"https://t.me/{SUPPORT_CHAT}"),
            ],
            [InlineKeyboardButton("❓ ʜᴇʟᴘ", callback_data="help_menu")],
        ]
    )

    start_text = get_lang("start_message", lang, mention=user.mention)

    await message.reply_text(
        start_text,
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


@Client.on_message(filters.command("start") & filters.group)
async def start_group(client: Client, message: Message):
    """Handle /start in group chats"""
    lang = await db.get_group_language(message.chat.id)

    # Add group to active groups (assuming db.addgroup is async
    await db.add_active_group(message.chat.id, message.chat.title)

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("❓ ʜᴇʟᴘ", callback_data="help_menu")]]
    )

    group_start = get_lang("group_start", lang)
    await message.reply_text(group_start, reply_markup=keyboard)
