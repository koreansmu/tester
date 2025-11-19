from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from utils.helpers import get_lang
from utils.database import Database

db = Database()

def get_help_keyboard():
    """Get help menu keyboard"""
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
    """Handle /help command"""
    lang = await db.get_group_language(message.chat.id)
    help_text = get_lang("help_main", lang)
    
    await message.reply_text(
        help_text,
        reply_markup=get_help_keyboard()
    )

@Client.on_callback_query(filters.regex("^help_"))
async def help_callback(client: Client, callback: CallbackQuery):
    """Handle help menu callbacks"""
    data = callback.data
    lang = await db.get_group_language(callback.message.chat.id)
    
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
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("ʜᴇʟᴘ </>", callback_data="help_menu")]
        ])
    
    else:
        return
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    except:
        await callback.answer("Already on this page!", show_alert=False)
