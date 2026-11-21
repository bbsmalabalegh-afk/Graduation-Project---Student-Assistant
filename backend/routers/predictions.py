"""ربط موديل الـ AI بالسيرفر: تنبؤ سريع، تنبؤ لطالب محفوظ، سجل النتايج، وإحصائيات اللوحة."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from .. import services
from ..database import get_db
from ..deps import get_current_user, require_staff
from ..ml import predictor as ml
from ..schemas import AcademicRecordIn

router = APIRouter(tags=["AI Predictions"])


def _run_model(record: dict) -> tuple[dict, str]:
    try:
        p = ml.get_predictor()
    except RuntimeError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e))
    return p.predict(record).to_dict(), p.version


@router.post("/api/predict")
def quick_predict(body: AcademicRecordIn, user=Depends(get_current_user), con=Depends(get_db)):
    """تنبؤ سريع من الفورم من غير ما نربطه بطالب (ده اللي صفحة الـ Dashboard بتستخدمه)."""
    result, version = _run_model(body.model_dump())
    result["prediction_id"] = services.save_prediction(con, result, version, created_by=user["id"])
    result["model_version"] = version
    return result


@router.post("/api/students/{student_id}/predict")
def predict_for_student(
    student_id: int,
    body: Optional[AcademicRecordIn] = None,
    user=Depends(require_staff), con=Depends(get_db),
):
    """لو بعت درجات في الـ body: بتتحفظ كسجل جديد وبعدين نتنبأ.
    لو مبعتش: بنستخدم آخر سجل درجات محفوظ للطالب."""
    try:
        if body is not None:
            record = services.add_record(con, student_id, body.model_dump(), created_by=user["id"])
        else:
            record = services.latest_record(con, student_id)
    except services.NotFound as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
    result, version = _run_model(record)
    result["prediction_id"] = services.save_prediction(
        con, result, version, student_id=student_id, record_id=record["id"], created_by=user["id"])
    result["model_version"] = version
    result["student_id"] = student_id
    result["record_id"] = record["id"]
    return result


@router.get("/api/students/{student_id}/predictions")
def student_predictions(student_id: int, user=Depends(get_current_user), con=Depends(get_db)):
    if user["role"] == "student":
        mine = services.get_student_by_user(con, user["id"])
        if mine is None or mine["id"] != student_id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only view your own results")
    try:
        return services.list_predictions(con, student_id)
    except services.NotFound as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.get("/api/dashboard/stats")
def stats(_=Depends(require_staff), con=Depends(get_db)):
    """أرقام جاهزة لرسومات لوحة التحكم (أحمد)."""
    return services.dashboard_stats(con)


@router.get("/api/model/info")
def model_info():
    return ml.model_status()
