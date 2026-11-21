"""الطلاب + إدخال الدرجات (السجل الأكاديمي)."""
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from .. import services
from ..database import get_db
from ..deps import get_current_user, require_staff
from ..schemas import AcademicRecordIn, StudentIn, StudentUpdate

router = APIRouter(prefix="/api/students", tags=["Students & Grades"])


def _404(e):
    return HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.get("")
def list_students(
    search: Optional[str] = Query(None, max_length=100),
    risk_level: Optional[Literal["High", "Medium", "Low"]] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _=Depends(require_staff), con=Depends(get_db),
):
    return services.list_students(con, search, risk_level, limit, offset)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_student(body: StudentIn, user=Depends(require_staff), con=Depends(get_db)):
    try:
        return services.create_student(con, body.model_dump(), created_by=user["id"])
    except services.Conflict as e:
        raise HTTPException(status.HTTP_409_CONFLICT, str(e))


@router.get("/me")
def my_student_profile(user=Depends(get_current_user), con=Depends(get_db)):
    """الطالب يشوف ملفه وآخر نتيجة ليه (لو الأدمن/الدكتور ربطه بحسابه)."""
    s = services.get_student_by_user(con, user["id"])
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No student profile linked to this account")
    return s


@router.get("/{student_id}")
def get_student(student_id: int, _=Depends(require_staff), con=Depends(get_db)):
    try:
        return services.get_student(con, student_id)
    except services.NotFound as e:
        raise _404(e)


@router.put("/{student_id}")
def update_student(student_id: int, body: StudentUpdate, _=Depends(require_staff), con=Depends(get_db)):
    try:
        return services.update_student(con, student_id, body.model_dump(exclude_unset=True))
    except services.NotFound as e:
        raise _404(e)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: int, _=Depends(require_staff), con=Depends(get_db)):
    try:
        services.delete_student(con, student_id)
    except services.NotFound as e:
        raise _404(e)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- الدرجات ----------
@router.post("/{student_id}/records", status_code=status.HTTP_201_CREATED)
def add_record(student_id: int, body: AcademicRecordIn, user=Depends(require_staff), con=Depends(get_db)):
    try:
        return services.add_record(con, student_id, body.model_dump(), created_by=user["id"])
    except services.NotFound as e:
        raise _404(e)


@router.get("/{student_id}/records")
def list_records(student_id: int, _=Depends(require_staff), con=Depends(get_db)):
    try:
        return services.list_records(con, student_id)
    except services.NotFound as e:
        raise _404(e)
