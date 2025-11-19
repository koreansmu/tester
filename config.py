import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_USERNAME = os.getenv("BOT_USERNAME", "")

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "Guardify")

PRETENDER_DB_URI = os.getenv("PRETENDER_DB_URI")
PRETENDER_DB_NAME = os.getenv("PRETENDER_DB_NAME", "Rankings")

OWNER_ID = int(os.getenv("OWNER_ID", "5960968099"))
SUDO_USERS = list(map(int, os.getenv("SUDO_USERS", "").split(","))) if os.getenv("SUDO_USERS") else []

SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL", "https://t.me/BillaSpace")
SUPPORT_CHAT = os.getenv("SUPPORT_CHAT", "https://t.me/BillaCore")
LOGGER_ID = int(os.getenv("LOGGER_ID", "0"))

# for nsfw p*rn modulation
NSFW_USE_FAST = os.getenv("NSFW_USE_FAST", "true").lower() in ("1", "true", "yes", "on")
NSFW_THRESHOLD = float(os.getenv("NSFW_THRESHOLD", "0.7"))

# default lang & caching timers
DEFAULT_LANG = os.getenv("DEFAULT_LANG", "en")
CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))
