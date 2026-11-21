"""السيرفر الرئيسي — Student Success Prediction System (Back-End: عبد الرحمن داود)

تشغيل محلي (من جذر الريبو):
    pip install -r requirements.txt
    uvicorn backend.main:app --reload
بعدها:
    http://127.0.0.1:8000/          -> الواجهات (index / login / dashboard)
    http://127.0.0.1:8000/docs      -> توثيق وتجربة كل الـ APIs (Swagger)
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config, services
from .database import connect, init_db
from .ml import predictor as ml
from .routers import auth, predictions, students


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if config.ADMIN_EMAIL and config.ADMIN_PASSWORD:
        con = connect()
        try:
            services.ensure_admin(con, config.ADMIN_EMAIL, config.ADMIN_PASSWORD, config.ADMIN_NAME)
        finally:
            con.close()
    try:  # نحمّل الموديل بدري عشان أول Request ميستناش
        ml.get_predictor()
    except RuntimeError as e:
        print("[WARN]", e)
    yield


app = FastAPI(
    title="Student Success Prediction API",
    description="Back-End لنظام التنبؤ بالتعثر الأكاديمي — مشروع التخرج",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(auth.users_router)
app.include_router(students.router)
app.include_router(predictions.router)


@app.get("/api/health", tags=["Health"])
def health():
    return {"status": "ok", "model": ml.model_status()["loaded"]}


# الواجهات — لازم تبقى آخر حاجة عشان متغطيش على /api و /docs
if config.FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")
