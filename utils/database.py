import logging
import time
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError
from config import MONGO_URI, DB_NAME
from utils import logger as ulogger

logger = logging.getLogger(__name__)

DEFAULT_DB_NAME = "BillaGuardian"

class Database:
    def __init__(self):
        try:
            if not ulogger.is_logging_enabled():
                logging.getLogger("motor").setLevel(logging.CRITICAL)
                logging.getLogger("pymongo").setLevel(logging.CRITICAL)
                logging.getLogger("urllib3").setLevel(logging.CRITICAL)
                logging.getLogger("asyncio").setLevel(logging.CRITICAL)
        except Exception:
            pass
        self.client = None
        self.db = None
        self.active_groups = None
        self.users = None
        self.groups_stats = None
        self.media_settings = None
        self.edit_settings = None
        self.slang_settings = None
        self.pretender_settings = None
        self.edit_auth = None
        self.media_auth = None
        self.slang_auth = None
        self.gban_users = None
        self.admin_logs = None
        self.group_languages = None
        self.overall_stats = None

    def __bool__(self):
        return bool(self.client)

    async def connect(self):
        if self.client is not None and self.db is not None:
            return
        db_name = DB_NAME if DB_NAME and isinstance(DB_NAME, str) and DB_NAME.strip() else DEFAULT_DB_NAME
        try:
            self.client = AsyncIOMotorClient(MONGO_URI)
            self.db = self.client[db_name]
            self.active_groups = self.db["active_groups"]
            self.users = self.db["users"]
            self.groups_stats = self.db["groups_stats"]
            self.media_settings = self.db["media_settings"]
            self.edit_settings = self.db["edit_settings"]
            self.slang_settings = self.db["slang_settings"]
            self.pretender_settings = self.db["pretender_settings"]
            self.edit_auth = self.db["edit_auth"]
            self.media_auth = self.db["media_auth"]
            self.slang_auth = self.db["slang_auth"]
            self.gban_users = self.db["gban_users"]
            self.admin_logs = self.db["admin_logs"]
            self.group_languages = self.db["group_languages"]
            self.overall_stats = self.db["overall_stats"]
            await self._create_indexes()
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self.client = None
            self.db = None
            return

    async def _create_indexes(self):
        try:
            await self.active_groups.create_index("chat_id", unique=True)
            await self.users.create_index("user_id", unique=True)
            await self.groups_stats.create_index("chat_id", unique=True)
            await self.media_settings.create_index("chat_id", unique=True)
            await self.edit_settings.create_index("chat_id", unique=True)
            await self.slang_settings.create_index("chat_id", unique=True)
            await self.pretender_settings.create_index("chat_id", unique=True)
            await self.gban_users.create_index("user_id", unique=True)
            await self.edit_auth.create_index([("chat_id", 1), ("user_id", 1)], unique=True)
            await self.media_auth.create_index([("chat_id", 1), ("user_id", 1)], unique=True)
            await self.slang_auth.create_index([("chat_id", 1), ("user_id", 1)], unique=True)
            await self.group_languages.create_index("chat_id", unique=True)
            await self.overall_stats.update_one(
                {"_id": "global"},
                {"$setOnInsert": {"total_groups": 0, "total_users": 0}},
                upsert=True,
            )
        except Exception as e:
            logger.warning("Error creating indexes: %s", e)

    async def _ensure(self):
        if self.client is None or self.db is None or self.users is None:
            await self.connect()

    async def add_active_group(self, chat_id, chat_title):
        await self._ensure()
        try:
            res = await self.active_groups.update_one(
                {"chat_id": chat_id},
                {"$set": {"chat_id": chat_id, "title": chat_title}},
                upsert=True,
            )
            if getattr(res, "upserted_id", None):
                await self.overall_stats.update_one(
                    {"_id": "global"},
                    {"$inc": {"total_groups": 1}},
                    upsert=True,
                )
        except DuplicateKeyError:
            pass

    async def remove_active_group(self, chat_id):
        await self._ensure()
        res = await self.active_groups.delete_one({"chat_id": chat_id})
        if getattr(res, "deleted_count", 0) > 0:
            await self.overall_stats.update_one(
                {"_id": "global"},
                {"$inc": {"total_groups": -1}},
                upsert=True,
            )

    async def get_active_groups(self):
        await self._ensure()
        return [g async for g in self.active_groups.find()]

    async def add_user(self, user_id, username=None, first_name=None):
        await self._ensure()
        try:
            res = await self.users.update_one(
                {"user_id": user_id},
                {"$set": {"user_id": user_id, "username": username, "first_name": first_name}},
                upsert=True,
            )
            if getattr(res, "upserted_id", None):
                await self.overall_stats.update_one(
                    {"_id": "global"},
                    {"$inc": {"total_users": 1}},
                    upsert=True,
                )
        except DuplicateKeyError:
            pass

    async def get_all_users(self):
        await self._ensure()
        return [u async for u in self.users.find()]

    async def set_media_delay(self, chat_id, delay):
        await self._ensure()
        await self.media_settings.update_one(
            {"chat_id": chat_id},
            {"$set": {"delay": delay, "enabled": True}},
            upsert=True,
        )

    async def get_media_delay(self, chat_id):
        await self._ensure()
        result = await self.media_settings.find_one({"chat_id": chat_id})
        return result.get("delay") if result and result.get("enabled") else None

    async def disable_media_guard(self, chat_id):
        await self._ensure()
        await self.media_settings.update_one(
            {"chat_id": chat_id},
            {"$set": {"enabled": False}},
            upsert=True,
        )

    async def set_edit_delay(self, chat_id, delay):
        await self._ensure()
        await self.edit_settings.update_one(
            {"chat_id": chat_id},
            {"$set": {"delay": delay, "enabled": True}},
            upsert=True,
        )

    async def get_edit_delay(self, chat_id):
        await self._ensure()
        result = await self.edit_settings.find_one({"chat_id": chat_id})
        return result.get("delay") if result and result.get("enabled") else None

    async def set_slang_filter(self, chat_id, enabled):
        await self._ensure()
        await self.slang_settings.update_one(
            {"chat_id": chat_id},
            {"$set": {"enabled": enabled}},
            upsert=True,
        )

    async def get_slang_status(self, chat_id):
        await self._ensure()
        result = await self.slang_settings.find_one({"chat_id": chat_id})
        return result.get("enabled", False) if result else False

    async def set_auto_clean(self, chat_id, enabled):
        await self._ensure()
        await self.groups_stats.update_one(
            {"chat_id": chat_id},
            {"$set": {"auto_clean": enabled}},
            upsert=True,
        )

    async def get_auto_clean_status(self, chat_id):
        await self._ensure()
        result = await self.groups_stats.find_one({"chat_id": chat_id})
        return result.get("auto_clean", False) if result else False

    async def set_pretender(self, chat_id, enabled):
        await self._ensure()
        await self.pretender_settings.update_one(
            {"chat_id": chat_id},
            {"$set": {"enabled": enabled}},
            upsert=True,
        )

    async def get_pretender_status(self, chat_id):
        await self._ensure()
        result = await self.pretender_settings.find_one({"chat_id": chat_id})
        return result.get("enabled", False) if result else False

    async def add_edit_auth(self, chat_id, user_id):
        await self._ensure()
        await self.edit_auth.update_one(
            {"chat_id": chat_id, "user_id": user_id},
            {"$set": {"chat_id": chat_id, "user_id": user_id}},
            upsert=True,
        )

    async def remove_edit_auth(self, chat_id, user_id):
        await self._ensure()
        await self.edit_auth.delete_one({"chat_id": chat_id, "user_id": user_id})

    async def is_edit_authorized(self, chat_id, user_id):
        await self._ensure()
        return await self.edit_auth.find_one({"chat_id": chat_id, "user_id": user_id}) is not None

    async def get_edit_auth_list(self, chat_id):
        await self._ensure()
        return [u async for u in self.edit_auth.find({"chat_id": chat_id})]

    async def add_media_auth(self, chat_id, user_id):
        await self._ensure()
        await self.media_auth.update_one(
            {"chat_id": chat_id, "user_id": user_id},
            {"$set": {"chat_id": chat_id, "user_id": user_id}},
            upsert=True,
        )

    async def remove_media_auth(self, chat_id, user_id):
        await self._ensure()
        await self.media_auth.delete_one({"chat_id": chat_id, "user_id": user_id})

    async def is_media_authorized(self, chat_id, user_id):
        await self._ensure()
        return await self.media_auth.find_one({"chat_id": chat_id, "user_id": user_id}) is not None

    async def get_media_auth_list(self, chat_id):
        await self._ensure()
        return [u async for u in self.media_auth.find({"chat_id": chat_id})]

    async def add_slang_auth(self, chat_id, user_id):
        await self._ensure()
        await self.slang_auth.update_one(
            {"chat_id": chat_id, "user_id": user_id},
            {"$set": {"chat_id": chat_id, "user_id": user_id}},
            upsert=True,
        )

    async def remove_slang_auth(self, chat_id, user_id):
        await self._ensure()
        await self.slang_auth.delete_one({"chat_id": chat_id, "user_id": user_id})

    async def is_slang_authorized(self, chat_id, user_id):
        await self._ensure()
        return await self.slang_auth.find_one({"chat_id": chat_id, "user_id": user_id}) is not None

    async def get_slang_auth_list(self, chat_id):
        await self._ensure()
        return [u async for u in self.slang_auth.find({"chat_id": chat_id})]

    async def add_gban(self, user_id, reason=None, duration=None):
        await self._ensure()
        await self.gban_users.update_one(
            {"user_id": user_id},
            {"$set": {
                "user_id": user_id,
                "reason": reason,
                "duration": duration,
                "timestamp": time.time()
            }},
            upsert=True
        )

    async def remove_gban(self, user_id):
        await self._ensure()
        await self.gban_users.delete_one({"user_id": user_id})

    async def is_gbanned(self, user_id):
        await self._ensure()
        result = await self.gban_users.find_one({"user_id": user_id})
        if not result:
            return False
        if result.get("duration"):
            elapsed = time.time() - result.get("timestamp", 0)
            if elapsed > result.get("duration") * 60:
                await self.remove_gban(user_id)
                return False
        return True

    async def get_gban_list(self):
        await self._ensure()
        return [u async for u in self.gban_users.find()]

    async def set_group_language(self, chat_id, lang):
        await self._ensure()
        await self.group_languages.update_one(
            {"chat_id": chat_id},
            {"$set": {"language": lang}},
            upsert=True
        )

    async def get_group_language(self, chat_id):
        await self._ensure()
        result = await self.group_languages.find_one({"chat_id": chat_id})
        return result.get("language", "en") if result else "en"

    async def log_admin_action(self, chat_id, admin_id, action, target_user=None):
        await self._ensure()
        await self.admin_logs.insert_one({
            "chat_id": chat_id,
            "admin_id": admin_id,
            "action": action,
            "target_user": target_user,
            "timestamp": time.time()
        })

    async def get_admin_logs(self, chat_id, limit=50):
        await self._ensure()
        cursor = self.admin_logs.find({"chat_id": chat_id}).sort("timestamp", -1).limit(limit)
        return [l async for l in cursor]

    async def get_total_stats(self):
        await self._ensure()
        global_doc = await self.overall_stats.find_one({"_id": "global"}) or {"total_groups": 0, "total_users": 0}
        edit_enabled = await self.edit_settings.count_documents({"enabled": True})
        media_enabled = await self.media_settings.count_documents({"enabled": True})
        slang_enabled = await self.slang_settings.count_documents({"enabled": True})
        return {
            "total_groups": int(global_doc.get("total_groups", 0)),
            "total_users": int(global_doc.get("total_users", 0)),
            "edit_enabled": int(edit_enabled),
            "media_enabled": int(media_enabled),
            "slang_enabled": int(slang_enabled)
        }

    async def rebuild_overall_stats(self):
        await self._ensure()
        total_groups = await self.active_groups.count_documents({})
        total_users = await self.users.count_documents({})
        await self.overall_stats.update_one(
            {"_id": "global"},
            {"$set": {"total_groups": int(total_groups), "total_users": int(total_users)}},
            upsert=True
        )

    async def set_user_language(self, user_id, lang):
        await self._ensure()
        await self.users.update_one(
            {"user_id": user_id},
            {"$set": {"language": lang}},
            upsert=True
        )

    async def get_user_language(self, user_id):
        await self._ensure()
        result = await self.users.find_one({"user_id": user_id})
        return result.get("language", "en") if result else "en"
