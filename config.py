import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "27696582"))
API_HASH = os.getenv("API_HASH", "45fccefb72a57ff1b858339774b6d005")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")

# Bot Admin Configuration
OWNER_ID = int(os.getenv("OWNER_ID", "5960968099"))
SUDO_USERS = list(map(int, os.getenv("SUDO_USERS", "").split(","))) if os.getenv("SUDO_USERS") else []

LOGGER_ID = int(os.getenv("LOGGER_ID", "-1002398675912"))  # Group/Channel ID for logging

BOT_USERNAME = os.getenv("BOT_USERNAME", "GuardXBot")
SUPPORT_CHAT = os.getenv("SUPPORT_CHAT", "https://t.me/your_support_chat")

DEFAULT_LANG = "en"
CACHE_TTL = 3600  # 1 hour caching for now
