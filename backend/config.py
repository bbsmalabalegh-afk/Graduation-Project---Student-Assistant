"""إعدادات السيرفر — كل حاجة ممكن تتغير من متغيرات البيئة (Environment Variables)
عشان نفس الكود يشتغل Local وعلى Render من غير تعديل."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent          # .../backend
PROJECT_ROOT = BASE_DIR.parent                       # جذر الريبو

# قاعدة البيانات (SQLite محليًا). منفصلة عن students.db بتاع نسخة Streamlit القديمة.
DB_PATH = Path(os.getenv("DB_PATH", BASE_DIR / "data" / "app.db"))

# ملفات الموديل بتاع بسملة
MODEL_PATH = Path(os.getenv("MODEL_PATH", PROJECT_ROOT / "student_model.pkl"))
TRAIN_CSV = Path(os.getenv("TRAIN_CSV", PROJECT_ROOT / "data" / "train.csv"))
SCALER_PATH = Path(os.getenv("SCALER_PATH", BASE_DIR / "ml" / "scaler.joblib"))

# الواجهات (HTML/CSS/JS) — السيرفر بيعرضها على نفس الدومين
FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", PROJECT_ROOT / "fronted"))

# JWT — لازم تغيّر SECRET_KEY في الإنتاج (Render) لقيمة عشوائية طويلة
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-secret-change-me-in-production-0000")
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = int(os.getenv("TOKEN_EXPIRE_MINUTES", "480"))

# CORS: لو الواجهة اتفتحت من Live Server أو دومين تاني
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]

# حساب أدمن أولي (اختياري) — بيتعمل تلقائيًا أول ما السيرفر يقوم لو القيم دي موجودة
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ADMIN_NAME = os.getenv("ADMIN_NAME", "System Admin")
