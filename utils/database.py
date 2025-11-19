from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError
import logging
import asyncio
from config import MONGO_URI


logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        try:
            self.client = MongoClient(MONGO_URI)
            self.db = self.client["billa_guardian"]

            # Existing collections (for compatibility)
            self.active_groups = self.db["active_groups"]
            self.users = self.db["users"]

            # New collections
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

            # Collection to keep global/overall stats (single document)
            self.overall_stats = self.db["overall_stats"]

            # Create indexes
            self._create_indexes()
            logger.info("Database connected successfully")

        except ConnectionFailure as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def _create_indexes(self):
        """Create database indexes for better performance and uniqueness"""
        try:
            self.active_groups.create_index("chat_id", unique=True)
            self.users.create_index("user_id", unique=True)
            self.groups_stats.create_index("chat_id", unique=True)
            self.media_settings.create_index("chat_id", unique=True)
            self.edit_settings.create_index("chat_id", unique=True)
            self.slang_settings.create_index("chat_id", unique=True)
            self.pretender_settings.create_index("chat_id", unique=True)
            self.gban_users.create_index("user_id", unique=True)
            self.edit_auth.create_index([("chat_id", 1), ("user_id", 1)], unique=True)
            self.media_auth.create_index([("chat_id", 1), ("user_id", 1)], unique=True)
            self.slang_auth.create_index([("chat_id", 1), ("user_id", 1)], unique=True)
            self.group_languages.create_index("chat_id", unique=True)
            # overall_stats uses single document with _id = 'global'
            self.overall_stats.create_index("_id", unique=True)

            # Ensure the global stats document exists (idempotent)
            self.overall_stats.update_one(
                {"_id": "global"},
                {"$setOnInsert": {"total_groups": 0, "total_users": 0}},
                upsert=True,
            )
        except Exception as e:
            logger.warning(f"Error creating indexes: {e}")

    # Active Groups Methods
    async def add_active_group(self, chat_id: int, chat_title: str):
        """Add a group to active groups.

        This uses an upsert and only increments the overall total_groups when a new document
        was actually inserted. That prevents double-counting if the same chat is added twice.
        """
        try:
            res = self.active_groups.update_one(
                {"chat_id": chat_id},
                {"$set": {"chat_id": chat_id, "title": chat_title}},
                upsert=True,
            )
            # update_one sets upserted_id when insertion happened
            if getattr(res, "upserted_id", None) is not None:
                # increment global counter exactly once for new group
                self.overall_stats.update_one(
                    {"_id": "global"},
                    {"$inc": {"total_groups": 1}},
                    upsert=True,
                )
        except DuplicateKeyError:
            # If there is a race and duplicate key appears, do nothing — group already exists
            logger.debug("Attempted to insert duplicate active_group (ignored)")

    async def remove_active_group(self, chat_id: int):
        """Remove a group from active groups and decrement overall stats if removed."""
        res = self.active_groups.delete_one({"chat_id": chat_id})
        if getattr(res, "deleted_count", 0) > 0:
            # decrement global counter only if we actually removed a document
            self.overall_stats.update_one(
                {"_id": "global"},
                {"$inc": {"total_groups": -1}},
                upsert=True,
            )

    async def get_active_groups(self):
        """Get all active groups"""
        return list(self.active_groups.find())

    # User Methods
    async def add_user(self, user_id: int, username: str = None, first_name: str = None):
        """Add or update user and maintain overall user count without duplication."""
        try:
            res = self.users.update_one(
                {"user_id": user_id},
                {"$set": {"user_id": user_id, "username": username, "first_name": first_name}},
                upsert=True,
            )
            # if upsert created a new user, increment total_users
            if getattr(res, "upserted_id", None) is not None:
                self.overall_stats.update_one(
                    {"_id": "global"},
                    {"$inc": {"total_users": 1}},
                    upsert=True,
                )
        except DuplicateKeyError:
            logger.debug("Attempted to insert duplicate user (ignored)")

    async def get_all_users(self):
        """Get all users"""
        return list(self.users.find())

    # Media Settings
    async def set_media_delay(self, chat_id: int, delay: int):
        """Set media auto-delete delay in minutes"""
        self.media_settings.update_one(
            {"chat_id": chat_id},
            {"$set": {"delay": delay, "enabled": True}},
            upsert=True,
        )

    async def get_media_delay(self, chat_id: int):
        """Get media delay setting"""
        result = self.media_settings.find_one({"chat_id": chat_id})
        return result.get("delay") if result and result.get("enabled") else None

    async def disable_media_guard(self, chat_id: int):
        """Disable media guard"""
        self.media_settings.update_one(
            {"chat_id": chat_id},
            {"$set": {"enabled": False}},
            upsert=True,
        )

    # Edit Settings
    async def set_edit_delay(self, chat_id: int, delay: int):
        """Set edit message delete delay"""
        self.edit_settings.update_one(
            {"chat_id": chat_id},
            {"$set": {"delay": delay, "enabled": True}},
            upsert=True,
        )

    async def get_edit_delay(self, chat_id: int):
        """Get edit delay setting"""
        result = self.edit_settings.find_one({"chat_id": chat_id})
        return result.get("delay") if result and result.get("enabled") else None

    # Slang Settings
    async def set_slang_filter(self, chat_id: int, enabled: bool):
        """Enable/disable slang filter"""
        self.slang_settings.update_one(
            {"chat_id": chat_id},
            {"$set": {"enabled": enabled}},
            upsert=True,
        )

    async def get_slang_status(self, chat_id: int):
        """Get slang filter status"""
        result = self.slang_settings.find_one({"chat_id": chat_id})
        return result.get("enabled", False) if result else False

    # Auto Clean Settings
    async def set_auto_clean(self, chat_id: int, enabled: bool):
        """Enable/disable auto clean"""
        self.groups_stats.update_one(
            {"chat_id": chat_id},
            {"$set": {"auto_clean": enabled}},
            upsert=True,
        )

    async def get_auto_clean_status(self, chat_id: int):
        """Get auto clean status"""
        result = self.groups_stats.find_one({"chat_id": chat_id})
        return result.get("auto_clean", False) if result else False

    # Pretender Settings
    async def set_pretender(self, chat_id: int, enabled: bool):
        """Enable/disable pretender detection"""
        self.pretender_settings.update_one(
            {"chat_id": chat_id},
            {"$set": {"enabled": enabled}},
            upsert=True,
        )

    async def get_pretender_status(self, chat_id: int):
        """Get pretender status"""
        result = self.pretender_settings.find_one({"chat_id": chat_id})
        return result.get("enabled", False) if result else False

    # Authorization Methods
    async def add_edit_auth(self, chat_id: int, user_id: int):
        """Authorize user to edit messages without deletion"""
        self.edit_auth.update_one(
            {"chat_id": chat_id, "user_id": user_id},
            {"$set": {"chat_id": chat_id, "user_id": user_id}},
            upsert=True,
        )

    async def remove_edit_auth(self, chat_id: int, user_id: int):
        """Remove edit authorization"""
        self.edit_auth.delete_one({"chat_id": chat_id, "user_id": user_id})

    async def is_edit_authorized(self, chat_id: int, user_id: int):
        """Check if user is authorized for edits"""
        return self.edit_auth.find_one({"chat_id": chat_id, "user_id": user_id}) is not None

    async def get_edit_auth_list(self, chat_id: int):
        """Get list of edit authorized users"""
        return list(self.edit_auth.find({"chat_id": chat_id}))

    async def add_media_auth(self, chat_id: int, user_id: int):
        """Authorize user to send media without deletion"""
        self.media_auth.update_one(
            {"chat_id": chat_id, "user_id": user_id},
            {"$set": {"chat_id": chat_id, "user_id": user_id}},
            upsert=True,
        )

    async def remove_media_auth(self, chat_id: int, user_id: int):
        """Remove media authorization"""
        self.media_auth.delete_one({"chat_id": chat_id, "user_id": user_id})

    async def is_media_authorized(self, chat_id: int, user_id: int):
        """Check if user is authorized for media"""
        return self.media_auth.find_one({"chat_id": chat_id, "user_id": user_id}) is not None

    async def get_media_auth_list(self, chat_id: int):
        """Get list of media authorized users"""
        return list(self.media_auth.find({"chat_id": chat_id}))

    async def add_slang_auth(self, chat_id: int, user_id: int):
        """Authorize user to use slang without deletion"""
        self.slang_auth.update_one(
            {"chat_id": chat_id, "user_id": user_id},
            {"$set": {"chat_id": chat_id, "user_id": user_id}},
            upsert=True,
        )

    async def remove_slang_auth(self, chat_id: int, user_id: int):
        """Remove slang authorization"""
        self.slang_auth.delete_one({"chat_id": chat_id, "user_id": user_id})

    async def is_slang_authorized(self, chat_id: int, user_id: int):
        """Check if user is authorized for slang"""
        return self.slang_auth.find_one({"chat_id": chat_id, "user_id": user_id}) is not None

    async def get_slang_auth_list(self, chat_id: int):
        """Get list of slang authorized users"""
        return list(self.slang_auth.find({"chat_id": chat_id}))

    # Global Ban Methods
    async def add_gban(self, user_id: int, reason: str = None, duration: int = None):
        """Add user to global ban list"""
        try:
            self.gban_users.update_one(
                {"user_id": user_id},
                {"$set": {
                    "user_id": user_id,
                    "reason": reason,
                    "duration": duration,
                    "timestamp": asyncio.get_event_loop().time()
                }},
                upsert=True,
            )
        except DuplicateKeyError:
            logger.debug("Attempted to insert duplicate gban entry (ignored)")

    async def remove_gban(self, user_id: int):
        """Remove user from global ban"""
        self.gban_users.delete_one({"user_id": user_id})

    async def is_gbanned(self, user_id: int):
        """Check if user is globally banned"""
        result = self.gban_users.find_one({"user_id": user_id})
        if not result:
            return False

        # Check if temporary ban expired
        if result.get("duration"):
            import time
            elapsed = time.time() - result.get("timestamp", 0)
            if elapsed > result.get("duration") * 60:
                await self.remove_gban(user_id)
                return False
        return True

    async def get_gban_list(self):
        """Get all globally banned users"""
        return list(self.gban_users.find())

    # Language Settings
    async def set_group_language(self, chat_id: int, lang: str):
        """Set group language"""
        self.group_languages.update_one(
            {"chat_id": chat_id},
            {"$set": {"language": lang}},
            upsert=True,
        )

    async def get_group_language(self, chat_id: int):
        """Get group language"""
        result = self.group_languages.find_one({"chat_id": chat_id})
        return result.get("language", "en") if result else "en"

    # Admin Logging
    async def log_admin_action(self, chat_id: int, admin_id: int, action: str, target_user: int = None):
        """Log admin actions"""
        import time
        self.admin_logs.insert_one({
            "chat_id": chat_id,
            "admin_id": admin_id,
            "action": action,
            "target_user": target_user,
            "timestamp": time.time(),
        })

    async def get_admin_logs(self, chat_id: int, limit: int = 50):
        """Get admin logs for a group"""
        return list(self.admin_logs.find({"chat_id": chat_id}).sort("timestamp", -1).limit(limit))

    # Stats Methods
    async def get_total_stats(self):
        """Get overall bot statistics"""
        # Read global counters from overall_stats document to avoid recomputing counts every time
        global_doc = self.overall_stats.find_one({"_id": "global"}) or {"total_groups": 0, "total_users": 0}

        edit_enabled = self.edit_settings.count_documents({"enabled": True})
        media_enabled = self.media_settings.count_documents({"enabled": True})
        slang_enabled = self.slang_settings.count_documents({"enabled": True})

        return {
            "total_groups": int(global_doc.get("total_groups", 0)),
            "total_users": int(global_doc.get("total_users", 0)),
            "edit_enabled": int(edit_enabled),
            "media_enabled": int(media_enabled),
            "slang_enabled": int(slang_enabled),
        }

    # Utility: force-rebuild global counters (safe to run if ever out-of-sync)
    async def rebuild_overall_stats(self):
        """Recalculate totals from collections and overwrite global counters."""
        total_groups = self.active_groups.count_documents({})
        total_users = self.users.count_documents({})
        self.overall_stats.update_one(
            {"_id": "global"},
            {"$set": {"total_groups": int(total_groups), "total_users": int(total_users)}},
            upsert=True,
          )
