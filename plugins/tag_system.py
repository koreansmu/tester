from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import FloodWait
from utils.decorators import admin_only
from utils.helpers import get_lang
from utils.database import Database
import asyncio
import logging

db = Database()
logger = logging.getLogger(__name__)

active_tags = {}

@Client.on_message(filters.command("atag") & filters.group)
@admin_only
async def tag_admins(client: Client, message: Message):
    lang = await db.get_group_language(message.chat.id)
    
    if message.chat.id in active_tags:
        await message.reply_text(get_lang("tag_already_running", lang))
        return
    
    try:
        active_tags[message.chat.id] = True
        
        custom_text = " ".join(message.command[1:]) if len(message.command) > 1 else None
        
        admins = []
        async for member in client.get_chat_members(message.chat.id, filter="administrators"):
            if not member.user.is_bot:
                admins.append(member.user.mention)
        
        if not admins:
            await message.reply_text(get_lang("no_admins", lang))
            del active_tags[message.chat.id]
            return
        
        batch_size = 5
        for i in range(0, len(admins), batch_size):
            if message.chat.id not in active_tags:
                break
            
            batch = admins[i:i+batch_size]
            tag_text = " ".join(batch)
            
            if custom_text:
                tag_text = f"{custom_text}\n\n{tag_text}"
            
            await message.reply_text(tag_text)
            await asyncio.sleep(2)
        
        if message.chat.id in active_tags:
            del active_tags[message.chat.id]
            await message.reply_text(get_lang("tag_completed", lang))
    
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        logger.error(f"Error in atag: {e}")
        if message.chat.id in active_tags:
            del active_tags[message.chat.id]

@Client.on_message(filters.command("utag") & filters.group)
@admin_only
async def tag_users(client: Client, message: Message):
    lang = await db.get_group_language(message.chat.id)
    
    if message.chat.id in active_tags:
        await message.reply_text(get_lang("tag_already_running", lang))
        return
    
    try:
        active_tags[message.chat.id] = True
        
        custom_text = " ".join(message.command[1:]) if len(message.command) > 1 else None
        
        users = []
        async for member in client.get_chat_members(message.chat.id):
            if not member.user.is_bot and not member.user.is_deleted:
                users.append(member.user.mention)
                
                if len(users) >= 200:
                    break
        
        if not users:
            await message.reply_text(get_lang("no_users", lang))
            del active_tags[message.chat.id]
            return
        
        batch_size = 5
        for i in range(0, len(users), batch_size):
            if message.chat.id not in active_tags:
                break
            
            batch = users[i:i+batch_size]
            tag_text = " ".join(batch)
            
            if custom_text and i == 0:
                tag_text = f"{custom_text}\n\n{tag_text}"
            
            await message.reply_text(tag_text)
            await asyncio.sleep(3)
        
        if message.chat.id in active_tags:
            del active_tags[message.chat.id]
            await message.reply_text(get_lang("tag_completed", lang))
    
    except FloodWait as e:
        await asyncio.sleep(e.value)
    except Exception as e:
        logger.error(f"Error in utag: {e}")
        if message.chat.id in active_tags:
            del active_tags[message.chat.id]

@Client.on_message(filters.command("stop") & filters.group)
@admin_only
async def stop_tagging(client: Client, message: Message):
    lang = await db.get_group_language(message.chat.id)
    
    if message.chat.id in active_tags:
        del active_tags[message.chat.id]
        await message.reply_text(get_lang("tag_stopped", lang))
    else:
        await message.reply_text(get_lang("no_tag_running", lang))
