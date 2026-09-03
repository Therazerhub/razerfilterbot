# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    API_ID = os.getenv("API_ID")  # For Telethon if needed, but we use Bot API
    API_HASH = os.getenv("API_HASH")
    MONGO_URI = os.getenv("MONGO_URI")
    DB_NAME = os.getenv("DB_NAME", "telegram_filter_bot")
    ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split())) if os.getenv("ADMIN_IDS") else []
    FILE_CHANNELS = list(map(int, os.getenv("FILE_CHANNELS", "").split())) if os.getenv("FILE_CHANNELS") else []
    LOG_CHANNEL = int(os.getenv("LOG_CHANNEL")) if os.getenv("LOG_CHANNEL") else None
    # Feature toggles (default values, can be overridden in DB)
    FEATURES = {
        "clone_bot": False,
        "multiple_db": False,
        "premium_plans": False,
        "referrals": False,
        "force_subscribe": False,
        "request_to_join": False,
        "url_shortener": False,
        "token_verification": False,
        "pm_search": True,
        "auto_delete_pm": False,
        "stream_links": True,
        "download_links": True,
    }