import os
import json
import sqlite3
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
except ImportError:
    firebase_admin = None
    credentials = None
    firestore = None
from api.core.config import DB_PATH, FIREBASE_KEY_PATH, BASE_DIR

def get_firestore_client():
    """Firebase Firestore 클라이언트를 안전하게 초기화하고 반환합니다."""
    if firebase_admin is None:
        return None
    if not firebase_admin._apps:
        firebase_env = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        try:
            if firebase_env and firebase_env.strip().startswith("{"):
                cred_dict = json.loads(firebase_env)
                cred = credentials.Certificate(cred_dict)
            else:
                default_key_path = os.path.join(BASE_DIR, "serviceAccountKey.json")
                key_path = firebase_env if firebase_env else default_key_path
                if os.path.exists(key_path):
                    cred = credentials.Certificate(key_path)
                else:
                    return None
            firebase_admin.initialize_app(cred)
        except Exception as e:
            print(f"⚠️ Firebase 초기화 경고: {e}")
            return None
    try:
        return firestore.client()
    except Exception:
        return None

def init_sqlite_db():
    """로컬 SQLite 캐시 데이터베이스 스키마를 초기화합니다."""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_data (
            date TEXT PRIMARY KEY,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            value REAL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    conn.close()

def get_sqlite_connection():
    """SQLite 데이터베이스 커넥션을 반환합니다."""
    return sqlite3.connect(DB_PATH)
