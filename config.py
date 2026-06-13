"""
Merkezi yapılandırma modülü.
Tüm ayarları .env dosyasından okur.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# === API KEYS ===
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID", "")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "")

# === INSTAGRAM SETTINGS ===
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD", "")
INSTAGRAM_UPLOAD_ENABLED = os.getenv("INSTAGRAM_UPLOAD_ENABLED", "True").lower() == "true"

# === VİDEO AYARLARI ===
LANGUAGE = os.getenv("LANGUAGE", "tr")
VIDEOS_PER_DAY = int(os.getenv("VIDEOS_PER_DAY", "1"))
VIDEO_DURATION = int(os.getenv("VIDEO_DURATION_SECONDS", "58"))

# Video boyutu: Dikey format (Shorts/Reels)
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 30

# === DIZIN YAPISI ===
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
ASSETS_DIR = BASE_DIR / "assets"
TEMP_DIR = BASE_DIR / "temp"
TOPICS_DIR = BASE_DIR / "topics"

# Klasörleri oluştur
for d in [OUTPUT_DIR, ASSETS_DIR, TEMP_DIR, TOPICS_DIR]:
    d.mkdir(exist_ok=True)

# === MODEL AYARLARI ===
GEMINI_MODEL = "gemini-2.5-flash"   # Ücretsiz, hızlı

# === PLATFORM AYARLARI ===
YOUTUBE_CATEGORY_ID = "22"          # People & Blogs
YOUTUBE_PRIVACY = "public"          # public / private / unlisted

def validate_config():
    """API key'lerin ayarlandığını kontrol eder."""
    missing = []
    if not GEMINI_API_KEY or GEMINI_API_KEY == "buraya_yazin":
        missing.append("GEMINI_API_KEY")
    if not PEXELS_API_KEY or PEXELS_API_KEY == "buraya_yazin":
        missing.append("PEXELS_API_KEY")
    
    if INSTAGRAM_UPLOAD_ENABLED:
        if not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD:
            print("⚠️  UYARI: Instagram yüklemesi açık ama kullanıcı adı/şifre eksik.")
            return False

    if missing:
        print(f"⚠️  UYARI: Şu API key'ler .env dosyasında eksik: {', '.join(missing)}")
        return False
    return True
