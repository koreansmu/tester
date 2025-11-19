from pyrogram import Client, filters
from pyrogram.types import ChatMemberUpdated, Message
from utils.database import Database
from utils.cache import CacheManager
from config import LOGGER_ID
import logging

db = Database()
cache = CacheManager()
logger = logging.getLogger(__name__)

@Client.on_chat_member_updated()
async def track_bot_status(client: Client, update: ChatMemberUpdated):
    try:
        if update.new_chat_member and update.new_chat_member.user.id == (await client.get_me()).id:
            if update.new_chat_member.status in ["member", "administrator"]:
                await db.add_active_group(update.chat.id, update.chat.title)
                
                if LOGGER_ID and update.from_user:
                    added_by = update.from_user.first_name
                    username = f"@{update.from_user.username}" if update.from_user.username else "No username"
                    log_msg = f"✅ **Bot Added to Group**\n\n"
                    log_msg += f"👤 Added by: {added_by} ({username})\n"
                    log_msg += f"💬 Group: {update.chat.title}\n"
                    log_msg += f"🆔 Group ID: `{update.chat.id}`"
                    await client.send_message(LOGGER_ID, log_msg)
            
            elif update.new_chat_member.status in ["left", "kicked"]:
                await db.remove_active_group(update.chat.id)
                
                if LOGGER_ID and update.from_user:
                    removed_by = update.from_user.first_name
                    username = f"@{update.from_user.username}" if update.from_user.username else "No username"
                    log_msg = f"❌ **Bot Removed from Group**\n\n"
                    log_msg += f"👤 Removed by: {removed_by} ({username})\n"
                    log_msg += f"💬 Group: {update.chat.title}\n"
                    log_msg += f"🆔 Group ID: `{update.chat.id}`"
                    await client.send_message(LOGGER_ID, log_msg)
    
    except Exception as e:
        logger.error(f"Error tracking bot status: {e}")

@Client.on_message(filters.new_chat_members)
async def welcome_new_members(client: Client, message: Message):
    try:
        for user in message.new_chat_members:
            is_gbanned = cache.get_gban(user.id)
            if is_gbanned is None:
                is_gbanned = await db.is_gbanned(user.id)
                cache.set_gban(user.id, is_gbanned)
            
            if is_gbanned:
                try:
                    await message.chat.ban_member(user.id)
                    await message.reply_text(
                        f"⚠️ User {user.mention} is globally banned and has been removed."
                    )
                except Exception as e:
                    logger.error(f"Error banning gbanned user: {e}")
            else:
                await db.add_user(user.id, user.username, user.first_name)
    
    except Exception as e:
        logger.error(f"Error in new member handler: {e}")

@Client.on_message(filters.left_chat_member)
async def member_left(client: Client, message: Message):
    try:
        user = message.left_chat_member
        logger.info(f"User {user.id} left group {message.chat.id}")
    except Exception as e:
        logger.error(f"Error in left member handler: {e}")
