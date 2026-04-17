from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "teletriage.db"

# PostgreSQL settings
DB_HOST = os.getenv("TELETRIAGE_DB_HOST", "localhost")
DB_PORT = int(os.getenv("TELETRIAGE_DB_PORT", "5432"))
DB_NAME = os.getenv("TELETRIAGE_DB_NAME", "teletriage")
DB_USER = os.getenv("TELETRIAGE_DB_USER", "teletriage_user")
DB_PASSWORD = os.getenv("TELETRIAGE_DB_PASSWORD", "password")

APP_TITLE = "TeleTriage IGD System"
APP_ICON = "🚑"
ORGANIZATION_DEFAULT = "TeleTriage IGD"

API_HOST = os.getenv("TELETRIAGE_API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("TELETRIAGE_API_PORT", "8000"))
API_BASE_URL = os.getenv("TELETRIAGE_API_BASE_URL", f"http://{API_HOST}:{API_PORT}")
STREAMLIT_HOST = os.getenv("TELETRIAGE_STREAMLIT_HOST", "http://backend:8000")
STREAMLIT_PORT = int(os.getenv("TELETRIAGE_STREAMLIT_PORT", "8501"))


DEFAULT_EMERGENCY_PHONE = os.getenv("TELETRIAGE_EMERGENCY_PHONE", "119")
DEFAULT_ADMIN_USER = os.getenv("TELETRIAGE_ADMIN_USER", "admin")
DEFAULT_ADMIN_PASSWORD = os.getenv("TELETRIAGE_ADMIN_PASS", "ChangeMe123!")

AUTO_REFRESH_SECONDS = int(os.getenv("TELETRIAGE_AUTO_REFRESH_SECONDS", "5"))
GPS_PUSH_SECONDS = int(os.getenv("TELETRIAGE_GPS_PUSH_SECONDS", "5"))
VIDEO_CALL_BASE_URL = os.getenv("TELETRIAGE_VIDEO_CALL_BASE_URL", "https://meet.jit.si")
VIDEO_CALL_PREFIX = os.getenv("TELETRIAGE_VIDEO_CALL_PREFIX", "teletriage")

DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
