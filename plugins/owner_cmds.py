from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import UserIsBlocked, PeerIdInvalid
from utils.decorators import owner_only, sudo_only
from utils.helpers import get_lang
from utils.database import Database
from utils import cache
from config import OWNER_ID, SUDO_USERS
import asyncio
import logging
import subprocess
import io
import tempfile
import os
import contextlib

db = Database()
logger = logging.getLogger(__name__)


@Client.on_message(filters.command(["activegc", "ac"]))
@sudo_only
async def active_groups(client: Client, message: Message):
    """Show active groups with invite links"""
    lang = await db.get_group_language(message.chat.id)

    try:
        groups = await db.get_active_groups()

        if not groups:
            await message.reply_text(get_lang("no_active_groups", lang))
            return

        text = get_lang("active_groups_header", lang, count=len(groups)) + "\n\n"

        for idx, group in enumerate(groups, 1):
            chat_id = group.get("chat_id")
            title = group.get("title", "Unknown")

            try:
                chat = await client.get_chat(chat_id)

                # Prefer existing invite link if available
                invite_link = getattr(chat, "invite_link", None)
                if invite_link:
                    text += f"{idx}. [{title}]({invite_link})\n"
                else:
                    # Only try to create/export an invite link if we don't already have one
                    try:
                        invite_link = await client.export_chat_invite_link(chat_id)
                        text += f"{idx}. [{title}]({invite_link})\n"
                    except Exception:
                        text += f"{idx}. {title} (No access)\n"

            except Exception:
                text += f"{idx}. {title} (Unavailable)\n"

        # Split if too long
        if len(text) > 4000:
            for i in range(0, len(text), 4000):
                await message.reply_text(text[i : i + 4000], disable_web_page_preview=True)
        else:
            await message.reply_text(text, disable_web_page_preview=True)

    except Exception as e:
        logger.error(f"Error showing active groups: {e}")
        await message.reply_text(get_lang("error_occurred", lang))


@Client.on_message(filters.command("bcast"))
@owner_only
async def broadcast(client: Client, message: Message):
    """Broadcast message to all users/groups"""
    lang = "en"

    if len(message.command) < 2 and not message.reply_to_message:
        await message.reply_text(get_lang("bcast_usage", lang))
        return

    # Determine target
    target = "all"
    if len(message.command) >= 2:
        if message.command[1] == "-users":
            target = "users"
        elif message.command[1] == "-groups":
            target = "groups"

    # Get broadcast message
    if message.reply_to_message:
        bcast_msg = message.reply_to_message
    else:
        # safer extraction of text after the command flags
        parts = message.text.split(None, 2)
        if len(parts) >= 3:
            bcast_msg = parts[2]
        elif len(parts) == 2:
            bcast_msg = parts[1]
        else:
            await message.reply_text(get_lang("bcast_usage", lang))
            return

    status_msg = await message.reply_text(get_lang("bcast_started", lang))

    success = 0
    failed = 0

    try:
        if target in ["all", "users"]:
            users = await db.get_all_users()
            for user in users:
                try:
                    uid = user.get("user_id")
                    if isinstance(bcast_msg, str):
                        await client.send_message(uid, bcast_msg)
                    else:
                        await bcast_msg.copy(uid)
                    success += 1
                    await asyncio.sleep(0.05)  # Rate limiting
                except (UserIsBlocked, PeerIdInvalid):
                    failed += 1
                except Exception as e:
                    logger.error(f"Broadcast error to user {user.get('user_id')}: {e}")
                    failed += 1

        if target in ["all", "groups"]:
            groups = await db.get_active_groups()
            for group in groups:
                try:
                    gid = group.get("chat_id")
                    if isinstance(bcast_msg, str):
                        await client.send_message(gid, bcast_msg)
                    else:
                        await bcast_msg.copy(gid)
                    success += 1
                    await asyncio.sleep(0.05)
                except Exception as e:
                    logger.error(f"Broadcast error to group {group.get('chat_id')}: {e}")
                    failed += 1

        await status_msg.edit_text(get_lang("bcast_completed", lang, success=success, failed=failed))

    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        await status_msg.edit_text(get_lang("error_occurred", lang))


@Client.on_message(filters.command("gban"))
@owner_only
async def global_ban(client: Client, message: Message):
    """Globally ban a user"""
    lang = "en"

    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        reason = " ".join(message.command[1:]) if len(message.command) > 1 else "No reason"
    elif len(message.command) >= 2:
        try:
            user_id = int(message.command[1])
            reason = " ".join(message.command[2:]) if len(message.command) > 2 else "No reason"
        except ValueError:
            await message.reply_text(get_lang("invalid_user", lang))
            return
    else:
        await message.reply_text(get_lang("gban_usage", lang))
        return

    await db.add_gban(user_id, reason)
    try:
        cache.set_gban(user_id, True)
    except Exception:
        logger.debug("cache.set_gban failed (cache not available)")

    await message.reply_text(get_lang("gban_success", lang, user_id=user_id, reason=reason))


@Client.on_message(filters.command("ungban"))
@owner_only
async def un_global_ban(client: Client, message: Message):
    """Remove global ban"""
    lang = "en"

    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    elif len(message.command) >= 2:
        try:
            user_id = int(message.command[1])
        except ValueError:
            await message.reply_text(get_lang("invalid_user", lang))
            return
    else:
        await message.reply_text(get_lang("ungban_usage", lang))
        return

    await db.remove_gban(user_id)
    try:
        cache.set_gban(user_id, False)
    except Exception:
        logger.debug("cache.set_gban failed (cache not available)")

    await message.reply_text(get_lang("ungban_success", lang, user_id=user_id))


@Client.on_message(filters.command("tgban"))
@owner_only
async def temp_global_ban(client: Client, message: Message):
    """Temporarily ban a user globally"""
    lang = "en"

    if message.reply_to_message and len(message.command) >= 2:
        user_id = message.reply_to_message.from_user.id
        try:
            duration = int(message.command[1])
            reason = " ".join(message.command[2:]) if len(message.command) > 2 else "No reason"
        except ValueError:
            await message.reply_text(get_lang("invalid_number", lang))
            return
    elif len(message.command) >= 3:
        try:
            user_id = int(message.command[1])
            duration = int(message.command[2])
            reason = " ".join(message.command[3:]) if len(message.command) > 3 else "No reason"
        except ValueError:
            await message.reply_text(get_lang("tgban_usage", lang))
            return
    else:
        await message.reply_text(get_lang("tgban_usage", lang))
        return

    await db.add_gban(user_id, reason, duration)
    try:
        cache.set_gban(user_id, True)
    except Exception:
        logger.debug("cache.set_gban failed (cache not available)")

    await message.reply_text(get_lang("tgban_success", lang, user_id=user_id, duration=duration, reason=reason))


@Client.on_message(filters.command("gbanlist"))
@sudo_only
async def gban_list(client: Client, message: Message):
    """Show globally banned users"""
    lang = "en"

    gbanned = await db.get_gban_list()

    if not gbanned:
        await message.reply_text(get_lang("no_gbanned", lang))
        return

    text = get_lang("gbanlist_header", lang, count=len(gbanned)) + "\n\n"
    for idx, user in enumerate(gbanned, 1):
        reason = user.get("reason", "No reason")
        duration = user.get("duration")
        duration_text = f" ({duration}m)" if duration else ""
        text += f"{idx}. `{user['user_id']}` - {reason}{duration_text}\n"

    await message.reply_text(text)


def _send_large_output_as_file(message: Message, client: Client, content: str, filename: str = "result.txt"):
    """
    Helper to write content to a temp file and send as a document.
    Returns True if sent, False otherwise.
    """
    try:
        tf = tempfile.NamedTemporaryFile(delete=False, prefix="res_", suffix=".txt")
        tf_name = tf.name
        with open(tf_name, "w", encoding="utf-8") as f:
            f.write(content)
        # send as document
        # We use reply so it goes to same chat
        # The caller should await this coroutine; to keep helper sync-returning, return filename and caller will send
        return tf_name
    except Exception as e:
        logger.error(f"Failed to write temp file: {e}")
        return None


@Client.on_message(filters.command("eval"))
@owner_only
async def evaluate_code(client: Client, message: Message):
    """Evaluate Python code (owner only). Only OWNER_ID may use this command."""
    # extra guard: only allow configured OWNER_ID (logger id)
    if not message.from_user or message.from_user.id != OWNER_ID:
        await message.reply_text("You are not authorized to use this command.")
        return

    if len(message.command) < 2:
        await message.reply_text("Usage: `/eval <code>`")
        return

    code = message.text.split(None, 1)[1]

    stdout_buf = io.StringIO()
    result_repr = None
    exc = None

    try:
        # Try eval first (for expressions)
        with contextlib.redirect_stdout(stdout_buf):
            try:
                res = eval(code, globals(), locals())
                # If coroutine, await it
                if asyncio.iscoroutine(res):
                    res = await res
                result_repr = repr(res)
            except SyntaxError:
                # Not an expression — try exec
                loc = {}
                exec(code, globals(), loc)
                # if user stored something in _ret, use it
                if "_ret" in loc:
                    result_repr = repr(loc["_ret"])
                else:
                    result_repr = ""
    except Exception as e:
        exc = e
        logger.exception("Eval execution error")

    stdout_value = stdout_buf.getvalue() or ""
    parts = []
    if stdout_value:
        parts.append("STDOUT:\n" + stdout_value)
    if result_repr:
        parts.append("RESULT:\n" + result_repr)
    if exc:
        parts.append("ERROR:\n" + repr(exc))

    final_output = "\n\n".join(parts).strip() or "No output"

    # Telegram message length safety threshold
    if len(final_output) > 4000:
        tf_name = _send_large_output_as_file(message, client, final_output)
        if tf_name:
            try:
                await message.reply_document(document=tf_name, caption="Result (too long, sent as file)")
            finally:
                try:
                    os.remove(tf_name)
                except Exception:
                    pass
        else:
            await message.reply_text("Failed to write/send result file.")
    else:
        await message.reply_text(f"```\n{final_output}\n```")


@Client.on_message(filters.command("sh"))
@owner_only
async def shell_command(client: Client, message: Message):
    """Execute shell command (owner only). Only OWNER_ID may use this command."""
    # extra guard: only allow configured OWNER_ID (logger id)
    if not message.from_user or message.from_user.id != OWNER_ID:
        await message.reply_text("You are not authorized to use this command.")
        return

    if len(message.command) < 2:
        await message.reply_text("Usage: `/sh <command>`")
        return

    cmd = message.text.split(None, 1)[1]

    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        output = (result.stdout or "") + (result.stderr or "")
    except Exception as e:
        output = f"Execution error: {e}"
        logger.exception("Shell command execution failed")

    if not output:
        output = "No output"

    if len(output) > 4000:
        tf_name = _send_large_output_as_file(message, client, output)
        if tf_name:
            try:
                await message.reply_document(document=tf_name, caption="Command output (too long, sent as file)")
            finally:
                try:
                    os.remove(tf_name)
                except Exception:
                    pass
        else:
            await message.reply_text("Failed to write/send result file.")
    else:
        await message.reply_text(f"```\n{output}\n```")
