import os
import logging
from cachetools import TTLCache
from typing import Any, Optional
from config import CACHE_TTL
from utils import logger as ulogger

logger = logging.getLogger(__name__)

cache_manager = None

class CacheManager:
    def __init__(self, maxsize: int = 10000, ttl: int = CACHE_TTL):
        self.admin_cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self.settings_cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self.auth_cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self.gban_cache = TTLCache(maxsize=1000, ttl=ttl)
        try:
            if ulogger.is_logging_enabled():
                logger.info(f"Cache initialized with maxsize={maxsize}, ttl={ttl}s")
        except Exception:
            logger.info(f"Cache initialized with maxsize={maxsize}, ttl={ttl}s")

    async def load_from_db(self, db):
        if db is None:
            return
        if not hasattr(db, "get_gban_list"):
            return
        try:
            gban_users = await db.get_gban_list()
            count = 0
            for user in gban_users:
                uid = user.get("user_id") if isinstance(user, dict) else None
                if uid is not None:
                    self.gban_cache[uid] = True
                    count += 1
            try:
                if ulogger.is_logging_enabled():
                    logger.info(f"Loaded {count} gbanned users to cache")
            except Exception:
                logger.info(f"Loaded {count} gbanned users to cache")
        except Exception as e:
            logger.error(f"Error loading cache from DB: {e}")

    def get_admin_cache_key(self, chat_id: int) -> str:
        return f"admins:{chat_id}"

    def get_settings_cache_key(self, chat_id: int, setting: str) -> str:
        return f"settings:{chat_id}:{setting}"

    def get_auth_cache_key(self, chat_id: int, user_id: int, auth_type: str) -> str:
        return f"auth:{chat_id}:{user_id}:{auth_type}"

    def set_admins(self, chat_id: int, admins: list):
        key = self.get_admin_cache_key(chat_id)
        self.admin_cache[key] = admins

    def get_admins(self, chat_id: int) -> Optional[list]:
        key = self.get_admin_cache_key(chat_id)
        return self.admin_cache.get(key)

    def clear_admins(self, chat_id: int):
        key = self.get_admin_cache_key(chat_id)
        if key in self.admin_cache:
            del self.admin_cache[key]

    def set_setting(self, chat_id: int, setting: str, value: Any):
        key = self.get_settings_cache_key(chat_id, setting)
        self.settings_cache[key] = value

    def get_setting(self, chat_id: int, setting: str) -> Optional[Any]:
        key = self.get_settings_cache_key(chat_id, setting)
        return self.settings_cache.get(key)

    def set_auth(self, chat_id: int, user_id: int, auth_type: str, value: bool):
        key = self.get_auth_cache_key(chat_id, user_id, auth_type)
        self.auth_cache[key] = value

    def get_auth(self, chat_id: int, user_id: int, auth_type: str) -> Optional[bool]:
        key = self.get_auth_cache_key(chat_id, user_id, auth_type)
        return self.auth_cache.get(key)

    def set_gban(self, user_id: int, value: bool):
        self.gban_cache[user_id] = value

    def get_gban(self, user_id: int) -> Optional[bool]:
        return self.gban_cache.get(user_id)

    def clear_all(self):
        self.admin_cache.clear()
        self.settings_cache.clear()
        self.auth_cache.clear()
        self.gban_cache.clear()
        try:
            if ulogger.is_logging_enabled():
                logger.info("All caches cleared")
        except Exception:
            logger.info("All caches cleared")

async def init_cache(db=None, maxsize: int = 10000, ttl: int = CACHE_TTL, load: bool = False):
    global cache_manager
    if cache_manager is None:
        cache_manager = CacheManager(maxsize=maxsize, ttl=ttl)
        if load:
            await cache_manager.load_from_db(db)
    return cache_manager

def get_cache() -> CacheManager:
    if cache_manager is None:
        raise RuntimeError("Cache not initialized. Call await init_cache(db, load=False) from startup.")
    return cache_manager
