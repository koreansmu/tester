import json
import os
import logging
from config import DEFAULT_LANG

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
        try:
            if not strings_dir:
                logger.warning("strings directory not found")
                return
            for file in os.listdir(strings_dir):
                if file.endswith(".json"):
                    lang_code = file.replace(".json", "")
                    with open(os.path.join(strings_dir, file), "r", encoding="utf-8") as f:
                        self.languages[lang_code] = json.load(f)
            logger.info(f"Loaded {len(self.languages)} language files from {strings_dir}")
        except Exception as e:
            logger.error(f"Error loading languages: {e}")
    def get_string(self, key, lang=DEFAULT_LANG, **kwargs):
        try:
            if lang not in self.languages:
                lang = DEFAULT_LANG
            text = self.languages.get(lang, {}).get(key, key)
            if kwargs:
                text = text.format(**kwargs)
            return text
        except Exception:
            return key

lang_manager = LanguageManager()

def get_lang(key, lang=DEFAULT_LANG, **kwargs):
    return lang_manager.get_string(key, lang, **kwargs)

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
    return candidates[1]

def load_slang_words():
    slang_variants = set()
    slang_file = _find_slang_file()
    try:
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
    except FileNotFoundError:
        os.makedirs(os.path.dirname(slang_file), exist_ok=True)
        with open(slang_file, "w", encoding="utf-8") as f:
            f.write("# Add slang words here\n")
        return set()
    except Exception:
        return set()
