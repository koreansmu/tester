import asyncio
import os
from pyrogram import Client, filters
from pyrogram.types import Message
from PIL import Image
from transformers import pipeline
from utils.database import Database
from utils.cache import CacheManager
from utils.helpers import get_lang, is_admin
from config import LOGGER_ID
import logging
import tempfile
import subprocess

db = Database()
cache = CacheManager()
logger = logging.getLogger(__name__)

# Initialize NSFW detection model
try:
    nsfw_classifier = pipeline("image-classification", model="Falconsai/nsfw_image_detection")
    logger.info("NSFW detection model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load NSFW model: {e}")
    nsfw_classifier = None

# NSFW threshold
NSFW_THRESHOLD = 0.7

def is_nsfw_content(image_path: str) -> tuple[bool, float, str]:
    """
    Check if image contains NSFW content
    Returns: (is_nsfw, confidence, label)
    """
    if not nsfw_classifier:
        return False, 0.0, "Model not loaded"
    
    try:
        image = Image.open(image_path).convert("RGB")
        results = nsfw_classifier(image)
        top_result = max(results, key=lambda x: x['score'])
        
        label = top_result['label']
        confidence = top_result['score']
        is_nsfw = label.lower() == "nsfw" and confidence >= NSFW_THRESHOLD
        
        return is_nsfw, confidence, label
    
    except Exception as e:
        logger.error(f"Error checking NSFW content: {e}")
        return False, 0.0, "Error"

def extract_video_frame(video_path: str, output_path: str, time_offset: str = "00:00:01") -> bool:
    """Extract a frame from video at specified time"""
    try:
        cmd = [
            'ffmpeg',
            '-ss', time_offset,
            '-i', video_path,
            '-vframes', '1',
            '-q:v', '2',
            '-y',
            output_path
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30
        )
        
        return result.returncode == 0 and os.path.exists(output_path)
    
    except Exception as e:
        logger.error(f"Error extracting video frame: {e}")
        return False

def trim_video(video_path: str, output_path: str, duration: int = 10) -> bool:
    """Trim video to first N seconds"""
    try:
        cmd = [
            'ffmpeg',
            '-i', video_path,
            '-t', str(duration),
            '-c', 'copy',
            '-y',
            output_path
        ]
        
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60
        )
        
        return result.returncode == 0
    
    except Exception as e:
        logger.error(f"Error trimming video: {e}")
        return False

async def check_and_handle_nsfw(client: Client, message: Message, file_path: str, media_type: str):
    """Check content for NSFW and handle accordingly"""
    try:
        lang = await db.get_group_language(message.chat.id)
        
        is_nsfw = False
        confidence = 0.0
        label = "Unknown"
        
        if media_type == "photo":
            is_nsfw, confidence, label = is_nsfw_content(file_path)
        
        elif media_type in ["video", "animation", "gif"]:
            frame_path = file_path + "_frame.jpg"
            
            if extract_video_frame(file_path, frame_path):
                is_nsfw, confidence, label = is_nsfw_content(frame_path)
                
                if os.path.exists(frame_path):
                    os.remove(frame_path)
            else:
                logger.warning(f"Failed to extract frame from {media_type}")
        
        if is_nsfw:
            await message.delete()
            
            warning_text = get_lang(
                "nsfw_detected",
                lang,
                user=message.from_user.mention,
                confidence=f"{confidence*100:.1f}%"
            )
            
            warning_msg = await client.send_message(
                message.chat.id,
                warning_text
            )
            
            if LOGGER_ID:
                log_msg = f"**NSFW Content Detected**\n\n"
                log_msg += f"User: {message.from_user.mention} (`{message.from_user.id}`)\n"
                log_msg += f"Group: {message.chat.title} (`{message.chat.id}`)\n"
                log_msg += f"Confidence: {confidence*100:.1f}%\n"
                log_msg += f"Label: {label}\n"
                log_msg += f"Type: {media_type}"
                
                await client.send_message(LOGGER_ID, log_msg)
            
            await asyncio.sleep(5)
            try:
                await warning_msg.delete()
            except:
                pass
            
            return True
        
        return False
    
    except Exception as e:
        logger.error(f"Error in NSFW check: {e}")
        return False
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass

@Client.on_message(filters.group & filters.photo)
async def check_photo_nsfw(client: Client, message: Message):
    """Check photos for NSFW content"""
    try:
        if await is_admin(client, message.chat.id, message.from_user.id):
            return
        
        if await db.is_gbanned(message.from_user.id):
            await message.delete()
            return
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            file_path = tmp_file.name
        
        await message.download(file_path)
        await check_and_handle_nsfw(client, message, file_path, "photo")
    
    except Exception as e:
        logger.error(f"Error checking photo NSFW: {e}")

@Client.on_message(filters.group & (filters.video | filters.animation))
async def check_video_nsfw(client: Client, message: Message):
    """Check videos/GIFs for NSFW content"""
    try:
        if await is_admin(client, message.chat.id, message.from_user.id):
            return
        
        if await db.is_gbanned(message.from_user.id):
            await message.delete()
            return
        
        if message.animation:
            media = message.animation
            media_type = "gif"
        else:
            media = message.video
            media_type = "video"
        
        if media.file_size > 50 * 1024 * 1024:
            logger.info(f"Skipping NSFW check for large video: {media.file_size} bytes")
            return
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
            file_path = tmp_file.name
        
        await message.download(file_path)
        
        if media.duration and media.duration > 10:
            trimmed_path = file_path + "_trimmed.mp4"
            if trim_video(file_path, trimmed_path, duration=10):
                os.remove(file_path)
                file_path = trimmed_path
        
        await check_and_handle_nsfw(client, message, file_path, media_type)
    
    except Exception as e:
        logger.error(f"Error checking video NSFW: {e}")
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass

@Client.on_message(filters.group & filters.sticker)
async def check_sticker_nsfw(client: Client, message: Message):
    """Check stickers for NSFW content"""
    try:
        if await is_admin(client, message.chat.id, message.from_user.id):
            return
        
        if await db.is_gbanned(message.from_user.id):
            await message.delete()
            return
        
        if message.sticker.is_animated or message.sticker.is_video:
            return
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webp") as tmp_file:
            file_path = tmp_file.name
        
        await message.download(file_path)
        
        try:
            img = Image.open(file_path)
            jpg_path = file_path.replace(".webp", ".jpg")
            img.convert("RGB").save(jpg_path, "JPEG")
            os.remove(file_path)
            file_path = jpg_path
        except:
            pass
        
        await check_and_handle_nsfw(client, message, file_path, "sticker")
    
    except Exception as e:
        logger.error(f"Error checking sticker NSFW: {e}")
