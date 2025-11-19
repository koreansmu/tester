import json
import os
import logging
import asyncio
from config import DEFAULT_LANG
from utils.decorators import admin_only, creator_only
from utils.cache import get_cache, init_cache

logger = logging.getLogger(__name__)

class LanguageManager:
    def __init__(self):
        self.languages = {}
        self.load_languages()

    def _find_strings_dir(self):
        base_dir = os.path.dirname(__file__)
        candidates = [
            os.path.join(base_dir, "strings"),
            os.path.abspath(os.path.join(base_dir, "..", "strings")),
            os.path.join(os.getcwd(), "strings")
        ]
        for p in candidates:
            if os.path.isdir(p):
                return p
        return None

    def load_languages(self):
        strings_dir = self._find_strings_dir()
        loaded = 0
        try:
            if not strings_dir:
                logger.warning("strings directory not found")
                logger.info("Loaded 0 language files 🍁")
                return
            for file in os.listdir(strings_dir):
                if file.endswith(".json"):
                    lang_code = file.replace(".json", "")
                    path = os.path.join(strings_dir, file)
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            self.languages[lang_code] = json.load(f)
                            loaded += 1
                    except Exception as e:
                        logger.warning("Failed to load language file %s: %s", path, e)
            logger.info(f"Loaded {loaded} language files 🍁")
        except Exception as e:
            logger.error(f"Error loading languages: {e}")
            logger.info("Loaded 0 language files 🍁")

    def get_string(self, key, lang=DEFAULT_LANG, **kwargs):
        try:
            if not lang:
                lang = DEFAULT_LANG
            if lang not in self.languages:
                lang = DEFAULT_LANG
            text = self.languages.get(lang, {}).get(key, key)
            if kwargs and isinstance(text, str):
                try:
                    text = text.format(**kwargs)
                except Exception:
                    pass
            return text
        except Exception:
            return key

lang_manager = LanguageManager()

def get_lang(key, lang=DEFAULT_LANG, **kwargs):
    return lang_manager.get_string(key, lang, **kwargs)

async def _ensure_cache():
    try:
        return get_cache()
    except Exception:
        try:
            from utils.database import Database
            db = Database()
            try:
                cache = await init_cache(db=db, use_db_once=False)
                return cache
            except Exception as e:
                logger.warning("init_cache failed in helpers: %s", e)
        except Exception as e:
            logger.warning("Could not import Database for cache init in helpers: %s", e)
        class _FallbackCache:
            def get_setting(self, key, setting=None):
                return None
            def set_setting(self, key, setting, value):
                return None
        return _FallbackCache()

async def get_user_lang(user_id: int) -> str:
    cache = await _ensure_cache()
    try:
        lang = await asyncio.to_thread(lambda: cache.get_setting(user_id, "language"))
    except Exception:
        lang = None
    if lang:
        return lang
    from utils.database import Database
    db = Database()
    try:
        lang = await db.get_user_language(user_id) or DEFAULT_LANG
    except Exception:
        lang = DEFAULT_LANG
    try:
        await asyncio.to_thread(lambda: cache.set_setting(user_id, "language", lang))
    except Exception:
        pass
    return lang

async def get_group_lang(chat_id: int) -> str:
    cache = await _ensure_cache()
    try:
        lang = await asyncio.to_thread(lambda: cache.get_setting(chat_id, "language"))
    except Exception:
        lang = None
    if lang:
        return lang
    from utils.database import Database
    db = Database()
    try:
        lang = await db.get_group_language(chat_id) or DEFAULT_LANG
    except Exception:
        lang = DEFAULT_LANG
    try:
        await asyncio.to_thread(lambda: cache.set_setting(chat_id, "language", lang))
    except Exception:
        pass
    return lang

async def is_admin(client, chat_id, user_id):
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in ["creator", "administrator"]
    except:
        return False

async def is_creator(client, chat_id, user_id):
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status == "creator"
    except:
        return False


def _find_slang_file():
    base_dir = os.path.dirname(__file__)
    candidates = [
        os.path.join(base_dir, "slang_words.txt"),
        os.path.abspath(os.path.join(base_dir, "..", "slang_words.txt")),
        os.path.join(os.getcwd(), "slang_words.txt")
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return os.path.join(base_dir, "slang_words.txt")

def load_slang_words():
    slang_variants = set()
    slang_file = _find_slang_file()
    try:
        if not os.path.isfile(slang_file):
            dirpath = os.path.dirname(slang_file)
            if dirpath and not os.path.isdir(dirpath):
                os.makedirs(dirpath, exist_ok=True)
            with open(slang_file, "w", encoding="utf-8") as f:
                f.write("# Add slang words here\n")
            return set()
        with open(slang_file, "r", encoding="utf-8") as f:
            for line in f:
                word = line.strip()
                if not word or word.startswith("#"):
                    continue
                lower = word.lower()
                slang_variants.add(lower)
                if word != lower:
                    slang_variants.add(word)
                title = lower.title()
                if title != word and title != lower:
                    slang_variants.add(title)
                upper = lower.upper()
                if upper != word and upper != lower:
                    slang_variants.add(upper)
        logger.info(f"Loaded {len(slang_variants)} slang word variants from {slang_file}")
        return slang_variants
    except Exception as e:
        logger.warning("Failed to load slang words: %s", e)
        return set()
