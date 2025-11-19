from functools import wraps
from pyrogram import Client
from pyrogram.types import Message
from config import OWNER_ID, SUDO_USERS
import logging

logger = logging.getLogger(__name__)

def owner_only(func):
    """Decorator to restrict command to owner only"""
    @wraps(func)
    async def wrapper(client: Client, message: Message):
        if message.from_user.id != OWNER_ID:
            await message.reply_text("🛑 This command is only for my Owner!")
            return
        return await func(client, message)
    return wrapper

def sudo_only(func):
    """Decorator to restrict command to sudo users and owner"""
    @wraps(func)
    async def wrapper(client: Client, message: Message):
        if message.from_user.id not in SUDO_USERS and message.from_user.id != OWNER_ID:
            await message.reply_text("🛑 This command requires my super user access!")
            return
        return await func(client, message)
    return wrapper

def admin_only(func):
    """Decorator to restrict command to group admins"""
    @wraps(func)
    async def wrapper(client: Client, message: Message):
        if message.chat.type == "private":
            await message.reply_text("❌ This command is for groups only!")
            return
        
        try:
            member = await client.get_chat_member(message.chat.id, message.from_user.id)
            if member.status not in ["creator", "administrator"]:
                await message.reply_text("🛑 This command is for admins only!")
                return
        except Exception as e:
            logger.error(f"Error checking admin status: {e}")
            return
        
        return await func(client, message)
    return wrapper

def creator_only(func):
    """Decorator to restrict command to group creator only"""
    @wraps(func)
    async def wrapper(client: Client, message: Message):
        if message.chat.type == "private":
            await message.reply_text("🛑 This command is for groups only!")
            return
        
        try:
            member = await client.get_chat_member(message.chat.id, message.from_user.id)
            if member.status != "creator":
                await message.reply_text("🛑 This command is restricted to group creator only!")
                return
        except Exception as e:
            logger.error(f"Error checking creator status: {e}")
            return
        
        return await func(client, message)
    return wrapper
