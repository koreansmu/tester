import os
import logging
from typing import Any, Optional, Dict
from cachetools import TTLCache
import orjson
from config import CACHE_TTL
from utils import logger as ulogger

logger = logging.getLogger(__name__)

cache_manager = None

class CacheManager:
    def __init__(self, maxsize: int = 10000, ttl: int = CACHE_TTL, storage_file: Optional[str] = None):
        self.admin_cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self.settings_cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self.auth_cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self.gban_cache = TTLCache(maxsize=1000, ttl=ttl)
        base_dir = os.path.dirname(__file__)
        self.storage_file = storage_file or os.path.join(base_dir, "cache_data.json")
        try:
            if ulogger.is_logging_enabled():
                logger.info(f"Cache initialized maxsize={maxsize} ttl={ttl}s storage={self.storage_file}")
        except Exception:
            logger.info(f"Cache initialized maxsize={maxsize} ttl={ttl}s storage={self.storage_file}")

    async def load_from_db(self, db) -> None:
        if db is None or not hasattr(db, "get_gban_list"):
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
                    logger.info(f"Loaded {count} gbanned users from DB")
            except Exception:
                logger.info(f"Loaded {count} gbanned users from DB")
            self._save_to_file()
        except Exception as e:
            logger.error(f"Error loading cache from DB: {e}")

    def _serialize_cache(self) -> Dict[str, Any]:
        return {
            "admins": dict(self.admin_cache.items()),
            "settings": dict(self.settings_cache.items()),
            "auth": dict(self.auth_cache.items()),
            "gban": list(self.gban_cache.keys())
        }

    def _save_to_file(self) -> None:
        try:
            data = self._serialize_cache()
            b = orjson.dumps(data)
            dirpath = os.path.dirname(self.storage_file)
            if dirpath and not os.path.isdir(dirpath):
                os.makedirs(dirpath, exist_ok=True)
            with open(self.storage_file, "wb") as f:
                f.write(b)
            try:
                if ulogger.is_logging_enabled():
                    logger.info(f"Cache saved to {self.storage_file}")
            except Exception:
                logger.info(f"Cache saved to {self.storage_file}")
        except Exception as e:
            logger.error(f"Failed to save cache to file: {e}")

    def _load_from_file(self) -> None:
        try:
            if not os.path.isfile(self.storage_file):
                return
            with open(self.storage_file, "rb") as f:
                raw = f.read()
            if not raw:
                return
            data = orjson.loads(raw)
            admins = data.get("admins", {})
            for k, v in admins.items():
                self.admin_cache[k] = v
            settings = data.get("settings", {})
            for k, v in settings.items():
                self.settings_cache[k] = v
            auth = data.get("auth", {})
            for k, v in auth.items():
                self.auth_cache[k] = v
            gban = data.get("gban", [])
            for uid in gban:
                try:
                    self.gban_cache[int(uid)] = True
                except Exception:
                    self.gban_cache[uid] = True
            try:
                if ulogger.is_logging_enabled():
                    logger.info(f"Loaded cache from {self.storage_file}")
            except Exception:
                logger.info(f"Loaded cache from {self.storage_file}")
        except Exception as e:
            logger.error(f"Failed to load cache from file: {e}")

    def get_admin_cache_key(self, chat_id: int) -> str:
        return f"admins:{chat_id}"

    def get_settings_cache_key(self, chat_id: int, setting: str) -> str:
        return f"settings:{chat_id}:{setting}"

    def get_auth_cache_key(self, chat_id: int, user_id: int, auth_type: str) -> str:
        return f"auth:{chat_id}:{user_id}:{auth_type}"

    def set_admins(self, chat_id: int, admins: list, persist: bool = False) -> None:
        key = self.get_admin_cache_key(chat_id)
        self.admin_cache[key] = admins
        if persist:
            self._save_to_file()

    def get_admins(self, chat_id: int) -> Optional[list]:
        key = self.get_admin_cache_key(chat_id)
        return self.admin_cache.get(key)

    def clear_admins(self, chat_id: int, persist: bool = False) -> None:
        key = self.get_admin_cache_key(chat_id)
        if key in self.admin_cache:
            del self.admin_cache[key]
            if persist:
                self._save_to_file()

    def set_setting(self, chat_id: int, setting: str, value: Any, persist: bool = False) -> None:
        key = self.get_settings_cache_key(chat_id, setting)
        self.settings_cache[key] = value
        if persist:
            self._save_to_file()

    def get_setting(self, chat_id: int, setting: str) -> Optional[Any]:
        key = self.get_settings_cache_key(chat_id, setting)
        return self.settings_cache.get(key)

    def set_auth(self, chat_id: int, user_id: int, auth_type: str, value: bool, persist: bool = False) -> None:
        key = self.get_auth_cache_key(chat_id, user_id, auth_type)
        self.auth_cache[key] = value
        if persist:
            self._save_to_file()

    def get_auth(self, chat_id: int, user_id: int, auth_type: str) -> Optional[bool]:
        key = self.get_auth_cache_key(chat_id, user_id, auth_type)
        return self.auth_cache.get(key)

    def set_gban(self, user_id: int, value: bool = True, persist: bool = False) -> None:
        self.gban_cache[user_id] = value
        if persist:
            self._save_to_file()

    def get_gban(self, user_id: int) -> Optional[bool]:
        return self.gban_cache.get(user_id)

    def clear_all(self, persist: bool = False) -> None:
        self.admin_cache.clear()
        self.settings_cache.clear()
        self.auth_cache.clear()
        self.gban_cache.clear()
        if persist:
            self._save_to_file()
        try:
            if ulogger.is_logging_enabled():
                logger.info("All caches cleared")
        except Exception:
            logger.info("All caches cleared")

async def init_cache(db=None, maxsize: int = 10000, ttl: int = CACHE_TTL, use_db_once: bool = True, storage_file: Optional[str] = None):
    global cache_manager
    if cache_manager is None:
        cache_manager = CacheManager(maxsize=maxsize, ttl=ttl, storage_file=storage_file)
        cache_manager._load_from_file()
        if use_db_once and db is not None:
            try:
                await cache_manager.load_from_db(db)
            except Exception:
                pass
    return cache_manager

def get_cache() -> CacheManager:
    if cache_manager is None:
        raise RuntimeError("Cache not initialized. Call await init_cache(db, use_db_once=False) from startup.")
    return cache_manager
