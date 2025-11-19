import json
import os
import logging
from typing import Set
from config import DEFAULT_LANG

logger = logging.getLogger(__name__)

class LanguageManager:
    def __init__(self):
        self.languages = {}
        self.load_languages()
    
    def load_languages(self):
        strings_dir = "strings"
        try:
            for file in os.listdir(strings_dir):
                if file.endswith(".json"):
                    lang_code = file.replace(".json", "")
                    with open(os.path.join(strings_dir, file), 'r', encoding='utf-8') as f:
                        self.languages[lang_code] = json.load(f)
            logger.info(f"Loaded {len(self.languages)} language files")
        except Exception as e:
            logger.error(f"Error loading languages: {e}")
    
    def get_string(self, key: str, lang: str = DEFAULT_LANG, **kwargs) -> str:
        try:
            if lang not in self.languages:
                lang = DEFAULT_LANG
            text = self.languages.get(lang, {}).get(key, key)
            if kwargs:
                text = text.format(**kwargs)
            return text
        except Exception as e:
            logger.error(f"Error getting string {key}: {e}")
            return key

lang_manager = LanguageManager()

def get_lang(key: str, lang: str = DEFAULT_LANG, **kwargs) -> str:
    return lang_manager.get_string(key, lang, **kwargs)

async def is_admin(client, chat_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status in ["creator", "administrator"]
    except:
        return False

async def is_creator(client, chat_id: int, user_id: int) -> bool:
    try:
        member = await client.get_chat_member(chat_id, user_id)
        return member.status == "creator"
    except:
        return False

def load_slang_words() -> Set[str]:
    slang_variants = set()
    try:
        with open("slang_words.txt", 'r', encoding='utf-8') as f:
            for line in f:
                word = line.strip()
                if not word or word.startswith('#'):
                    continue
                lower = word.lower()
                slang_variants.add(lower)
                if lower != word:
                    slang_variants.add(word)
                title = lower.title()
                if title != word and title != lower:
                    slang_variants.add(title)
                upper = lower.upper()
                if upper != word and upper != lower:
                    slang_variants.add(upper)
        logger.info(f"Loaded {len(slang_variants)} slang word variants (including case variations)")
        return slang_variants
    except FileNotFoundError:
        logger.warning("slang_words.txt not found, creating empty file")
        with open("slang_words.txt", 'w', encoding='utf-8') as f:
            f.write("# Add slang words here (one per line)\n")
        return set()
    except Exception as e:
        logger.error(f"Error loading slang words: {e}")
        return set()
