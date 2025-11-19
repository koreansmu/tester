import os
import sys
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

from utils.decorators import sudo_only, owner_only
from utils.helpers import get_lang
from utils.database import Database
from config import LOGGER_ID, BOT_USERNAME

db = Database()

@Client.on_message(filters.command("restart") & filters.private)
@sudo_only
async def restart_cmd(client: Client, message: Message):
    """Restart the bot process (sudo only)."""
    lang = await db.get_group_language(message.chat.id)

    await message.reply_text(get_lang("admin_restart_reply", lang))

    try:
        # Log message
        try:
            await client.send_message(
                LOGGER_ID,
                get_lang(
                    "admin_restart_log",
                    lang,
                    bot=BOT_USERNAME,
                    user_id=message.from_user.id
                )
            )
        except Exception:
            pass

        await client.stop()

    except Exception as e:
        await message.reply_text(
            get_lang("admin_restart_error", lang, error=e)
        )

    os.execv(sys.executable, [sys.executable] + sys.argv)


@Client.on_message(filters.command("update") & filters.private)
@owner_only
async def update_cmd(client: Client, message: Message):
    """Owner-only: Pull latest from git and restart."""
    lang = await db.get_group_language(message.chat.id)

    args = message.text.split(maxsplit=1)
    commit_msg = args[1] if len(args) > 1 else None

    msg = await message.reply_text(get_lang("admin_update_reply", lang))

    try:
        proc = await asyncio.create_subprocess_shell(
            "git pull --no-rebase",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        out = stdout.decode().strip()
        err = stderr.decode().strip()

        # Build success message
        stdout_txt = ""
        stderr_txt = ""

        if out:
            stdout_txt = get_lang("admin_update_stdout", lang, stdout=out)
        if err:
            stderr_txt = get_lang("admin_update_stderr", lang, stderr=err)

        await msg.edit_text(
            get_lang(
                "admin_update_success",
                lang,
                code=proc.returncode,
                stdout=stdout_txt,
                stderr=stderr_txt
            )
            + "\n"
            + get_lang("admin_update_restart", lang)
        )

        # Log update
        maybe_msg = f"\nMessage: {commit_msg}" if commit_msg else ""
        try:
            await client.send_message(
                LOGGER_ID,
                get_lang(
                    "admin_update_log",
                    lang,
                    bot=BOT_USERNAME,
                    user_id=message.from_user.id,
                    code=proc.returncode,
                    maybe_msg=maybe_msg
                )
            )
        except Exception:
            pass

    except Exception as e:
        await msg.edit_text(
            get_lang("admin_update_failed", lang, error=e)
        )
        return

    try:
        await client.stop()
    except Exception:
        pass

    os.execv(sys.executable, [sys.executable] + sys.argv)
