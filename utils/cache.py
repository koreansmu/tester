import os
from cachetools import TTLCache
import logging
from typing import Any, Optional
from config import CACHE_TTL

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self, maxsize: int = 10000, ttl: int = CACHE_TTL):
        """Initialize cache manager with TTL cache"""
        self.admin_cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self.settings_cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self.auth_cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self.gban_cache = TTLCache(maxsize=1000, ttl=ttl)
        logger.info(f"Cache initialized with maxsize={maxsize}, ttl={ttl}s")
    
    async def load_from_db(self, db):
        """Pre-load critical data from database"""
        try:
            # Load gban users
            gban_users = await db.get_gban_list()
            for user in gban_users:
                self.gban_cache[user["user_id"]] = True
            
            logger.info(f"Loaded {len(gban_users)} gbanned users to cache")
        except Exception as e:
            logger.error(f"Error loading cache from DB: {e}")
    
    def get_admin_cache_key(self, chat_id: int) -> str:
        """Generate cache key for admins"""
        return f"admins:{chat_id}"
    
    def get_settings_cache_key(self, chat_id: int, setting: str) -> str:
        """Generate cache key for settings"""
        return f"settings:{chat_id}:{setting}"
    
    def get_auth_cache_key(self, chat_id: int, user_id: int, auth_type: str) -> str:
        """Generate cache key for authorization"""
        return f"auth:{chat_id}:{user_id}:{auth_type}"
    
    def set_admins(self, chat_id: int, admins: list):
        """Cache admin list for a chat"""
        key = self.get_admin_cache_key(chat_id)
        self.admin_cache[key] = admins
    
    def get_admins(self, chat_id: int) -> Optional[list]:
        """Get cached admin list"""
        key = self.get_admin_cache_key(chat_id)
        return self.admin_cache.get(key)
    
    def clear_admins(self, chat_id: int):
        """Clear admin cache for a chat"""
        key = self.get_admin_cache_key(chat_id)
        if key in self.admin_cache:
            del self.admin_cache[key]
    
    def set_setting(self, chat_id: int, setting: str, value: Any):
        """Cache a setting"""
        key = self.get_settings_cache_key(chat_id, setting)
        self.settings_cache[key] = value
    
    def get_setting(self, chat_id: int, setting: str) -> Optional[Any]:
        """Get cached setting"""
        key = self.get_settings_cache_key(chat_id, setting)
        return self.settings_cache.get(key)
    
    def set_auth(self, chat_id: int, user_id: int, auth_type: str, value: bool):
        """Cache authorization status"""
        key = self.get_auth_cache_key(chat_id, user_id, auth_type)
        self.auth_cache[key] = value
    
    def get_auth(self, chat_id: int, user_id: int, auth_type: str) -> Optional[bool]:
        """Get cached authorization status"""
        key = self.get_auth_cache_key(chat_id, user_id, auth_type)
        return self.auth_cache.get(key)
    
    def set_gban(self, user_id: int, value: bool):
        """Cache gban status"""
        self.gban_cache[user_id] = value
    
    def get_gban(self, user_id: int) -> Optional[bool]:
        """Get cached gban status"""
        return self.gban_cache.get(user_id)
    
    def clear_all(self):
        """Clear all caches"""
        self.admin_cache.clear()
        self.settings_cache.clear()
        self.auth_cache.clear()
        self.gban_cache.clear()
        logger.info("All caches cleared")
