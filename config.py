import os
from pathlib import Path
from dotenv import load_dotenv

# Załaduj zmienne środowiskowe z pliku .env
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Konfiguracja Discorda (Webhook)
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "").strip()

# Konfiguracja Telegrama (Alternatywa)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

# Konfiguracja Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip()

# Ścieżka do bazy danych
DATA_DIR = BASE_DIR / "data"
DATABASE_PATH = DATA_DIR / "jobs.db"

# Domyślne parametry wyszukiwania
TARGET_KEYWORDS = os.getenv("TARGET_KEYWORDS", "python").strip()
TARGET_SENIORITY = [s.strip().lower() for s in os.getenv("TARGET_SENIORITY", "trainee,junior").split(",") if s.strip()]
TARGET_CATEGORY = os.getenv("TARGET_CATEGORY", "backend").strip()

