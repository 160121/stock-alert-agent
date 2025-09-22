# app/utils/config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def validate():
    """Ensure required configs exist."""
    if not GEMINI_API_KEY:
        raise ValueError("⚠️ GEMINI_API_KEY missing in environment")
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("⚠️ TELEGRAM_BOT_TOKEN missing in environment")