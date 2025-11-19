import asyncio
import os
import subprocess
import tempfile
import logging
from PIL import Image
from pyrogram import Client, filters
from pyrogram.types import Message
from transformers import pipeline

from utils.database import Database
from utils.cache import CacheManager
from utils.helpers import get_lang, is_admin
from utils.decorators import creator_only
from config import LOGGER_ID, NSFW_USE_FAST, NSFW_THRESHOLD

db = Database()
cache = CacheManager()
logger = logging.getLogger(__name__)

USE_FAST_PROCESSOR = bool(NSFW_USE_FAST) if ("NSFW_USE_FAST" in globals() or 'NSFW_USE_FAST' in locals()) else True
NSFW_THRESHOLD = float(NSFW_THRESHOLD) if ("NSFW_THRESHOLD" in globals() or 'NSFW_THRESHOLD' in locals()) else 0.7

nsfw_classifier = None

def _bool_from_any(v):
    if isinstance(v, bool):
        return v
    if v is None:
        return True
    s = str(v).lower()
    return s in ("1", "true", "yes", "on", "fast")

def load_nsfw_model(use_fast=None):
    global nsfw_classifier, USE_FAST_PROCESSOR
    if use_fast is not None:
        USE_FAST_PROCESSOR = bool(use_fast)
    try:
        nsfw_classifier = pipeline(
            "image-classification",
            model="Falconsai/nsfw_image_detection",
            use_fast=USE_FAST_PROCESSOR
        )
    except Exception:
        nsfw_classifier = None

_env_use_fast = os.getenv("NSFW_USE_FAST", None)
if _env_use_fast is not None:
    try:
        USE_FAST_PROCESSOR = _bool_from_any(_env_use_fast)
    except:
        pass

load_nsfw_model()

def is_nsfw_content(image_path: str):
    if not nsfw_classifier:
        return False, 0.0, "Model"
    try:
        image = Image.open(image_path).convert("RGB")
        results = nsfw_classifier(image)
        top = max(results, key=lambda x: x.get("score", 0))
        label = top.get("label", "Unknown")
        score = float(top.get("score", 0.0))
        low_label = label.lower()
        is_nsfw = low_label in ["nsfw", "porn", "hentai"] and score >= NSFW_THRESHOLD
        return is_nsfw, score, label
    except Exception:
        return False, 0.0, "Error"

def extract_video_frame(video_path: str, output_path: str, time_offset: str = "00:00:01") -> bool:
    cmd = ["ffmpeg", "-ss", time_offset, "-i", video_path, "-vframes", "1", "-q:v", "2", "-y", output_path]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        return result.returncode == 0 and os.path.exists(output_path)
    except Exception:
        return False

def trim_video(video_path: str, output_path: str, duration: int = 10) -> bool:
    cmd = ["ffmpeg", "-i", video_path, "-t", str(duration), "-c", "copy", "-y", output_path]
    try:
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        return result.returncode == 0
    except Exception:
        return False

async def check_and_handle_nsfw(client: Client, message: Message, file_path: str, media_type: str):
    try:
        lang = await db.get_group_language(message.chat.id)
        is_nsfw = False
        confidence = 0.0
        label = "Unknown"

        if media_type == "photo":
            is_nsfw, confidence, label = is_nsfw_content(file_path)
        elif media_type in ["video", "animation", "gif", "sticker"]:
            frame_path = file_path + "_frame.jpg"
            if extract_video_frame(file_path, frame_path):
                is_nsfw, confidence, label = is_nsfw_content(frame_path)
                if os.path.exists(frame_path):
                    os.remove(frame_path)

        if is_nsfw:
            try:
                await message.delete()
            except:
                pass

            warning_text = get_lang(
                "nsfw_detected",
                lang,
                user=message.from_user.mention,
                confidence=f"{confidence*100:.1f}%"
            )

            try:
                warning_msg = await client.send_message(message.chat.id, warning_text)
            except:
                warning_msg = None

            if LOGGER_ID:
                log_text = get_lang(
                    "nsfw_log",
                    lang,
                    user=message.from_user.mention,
                    userid=message.from_user.id,
                    group=message.chat.title,
                    groupid=message.chat.id,
                    confidence=f"{confidence*100:.1f}%",
                    label=label,
                    mtype=media_type
                )
                try:
                    await client.send_message(LOGGER_ID, log_text)
                except:
                    pass

            if warning_msg:
                await asyncio.sleep(30)
                try:
                    await warning_msg.delete()
                except:
                    pass
            return True
        return False
    except Exception:
        return False
    finally:
        for p in [file_path, file_path + "_trimmed.mp4", file_path + "_frame.jpg"]:
            if os.path.exists(p):
                try:
                    os.remove(p)
                except:
                    pass

@Client.on_message(filters.command("antinsfw") & filters.group & creator_only)
async def nsfw_mode_command(client: Client, message: Message):
    arg = (message.text.split(maxsplit=1)[1] if len(message.command) > 1 else "").lower()
    lang = await db.get_group_language(message.chat.id)

    if arg in ["fast", "true", "1", "on"]:
        load_nsfw_model(use_fast=True)
        await message.reply(get_lang("nsfw_reloaded_fast", lang))
    elif arg in ["slow", "false", "0", "off"]:
        load_nsfw_model(use_fast=False)
        await message.reply(get_lang("nsfw_reloaded_slow", lang))
    else:
        mode = "fast" if USE_FAST_PROCESSOR else "slow"
        msg = (
            get_lang("nsfw_current_mode", lang, mode=mode)
            + "\n\n"
            + get_lang("nsfw_usage", lang)
            + "\n"
            + get_lang("nsfw_only_owner_change", lang)
        )
        await message.reply(msg)

@Client.on_message(filters.group & filters.photo)
async def check_photo_nsfw(client: Client, message: Message):
    if await is_admin(client, message.chat.id, message.from_user.id):
        return
    if await db.is_gbanned(message.from_user.id):
        await message.delete()
        return
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
        file_path = tmp.name
    await message.download(file_path)
    await check_and_handle_nsfw(client, message, file_path, "photo")

@Client.on_message(filters.group & (filters.video | filters.animation))
async def check_video_nsfw(client: Client, message: Message):
    if await is_admin(client, message.chat.id, message.from_user.id):
        return
    if await db.is_gbanned(message.from_user.id):
        await message.delete()
        return
    media = message.animation or message.video
    media_type = "gif" if message.animation else "video"
    if media.file_size and media.file_size > 50 * 1024 * 1024:
        return
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        file_path = tmp.name
    await message.download(file_path)
    if getattr(media, "duration", 0) and media.duration > 10:
        trimmed = file_path + "_trimmed.mp4"
        if trim_video(file_path, trimmed, 10):
            try:
                os.remove(file_path)
            except:
                pass
            file_path = trimmed
    await check_and_handle_nsfw(client, message, file_path, media_type)

@Client.on_message(filters.group & filters.sticker)
async def check_sticker_nsfw(client: Client, message: Message):
    if await is_admin(client, message.chat.id, message.from_user.id):
        return
    if await db.is_gbanned(message.from_user.id):
        await message.delete()
        return
    if message.sticker.is_animated or message.sticker.is_video:
        return
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webp") as tmp:
        file_path = tmp.name
    await message.download(file_path)
    try:
        img = Image.open(file_path)
        jpg_path = file_path.replace(".webp", ".jpg")
        img.convert("RGB").save(jpg_path, "JPEG")
        os.remove(file_path)
        file_path = jpg_path
    except Exception:
        pass
    await check_and_handle_nsfw(client, message, file_path, "sticker")
