import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 기본 디렉토리 및 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "stock_cache.db")
if not os.path.exists(DB_PATH):
    fallback_path = os.path.join(os.getcwd(), "api", "stock_cache.db")
    if os.path.exists(fallback_path):
        DB_PATH = fallback_path

FIREBASE_KEY_PATH = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", os.path.join(BASE_DIR, "serviceAccountKey.json"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# 서버 포트 및 CORS
PORT = int(os.getenv("PORT", 8090))
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",")]
