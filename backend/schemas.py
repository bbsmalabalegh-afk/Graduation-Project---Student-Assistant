"""شكل البيانات اللي داخلة وخارجة من الـ APIs (Pydantic) — بيعمل Validation تلقائي
ويرجع 422 لو في حقل ناقص أو قيمة برا المدى."""
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
Role = Literal["admin", "doctor", "student"]


# ---------------- Auth / Users ----------------
class RegisterIn(BaseModel):
    full_name: str = Field(min_length=3, max_length=100)
    email: str = Field(pattern=EMAIL_PATTERN, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=120)
    password: str = Field(min_length=1, max_length=128)


class UserCreateIn(RegisterIn):
    """الأدمن بس اللي يقدر يحدد الـ role (مثلًا يعمل حساب دكتور)."""
    role: Role = "doctor"


class UserOut(BaseModel):
    id: int
    full_name: str
    email: str
    role: Role
    created_at: Optional[str] = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------------- Students ----------------
class StudentIn(BaseModel):
    student_code: str = Field(min_length=1, max_length=30)
    full_name: str = Field(min_length=3, max_length=100)
    email: Optional[str] = Field(default=None, pattern=EMAIL_PATTERN, max_length=120)
    department: Optional[str] = Field(default=None, max_length=80)
    level: Optional[int] = Field(default=None, ge=1, le=7)


class StudentUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=3, max_length=100)
    email: Optional[str] = Field(default=None, pattern=EMAIL_PATTERN, max_length=120)
    department: Optional[str] = Field(default=None, max_length=80)
    level: Optional[int] = Field(default=None, ge=1, le=7)


# ---------------- Grades / Model input ----------------
class AcademicRecordIn(BaseModel):
    """نفس مدخلات موديل بسملة. الدرجات على نظام الداتا سِت: درجة الترم من 20، درجة القبول من 200."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "admission_grade": 130, "sem1_enrolled": 6, "sem1_approved": 5, "sem1_grade": 12.5,
        "sem2_enrolled": 6, "sem2_approved": 4, "sem2_grade": 11.8, "age_at_enrollment": 19,
        "tuition_up_to_date": True, "scholarship_holder": False}})

    admission_grade: float = Field(ge=0, le=200, description="درجة القبول (0-200)")
    sem1_enrolled: int = Field(ge=0, le=30, description="عدد مواد الترم الأول المسجلة")
    sem1_approved: int = Field(ge=0, le=30, description="عدد مواد الترم الأول اللي نجح فيها")
    sem1_grade: float = Field(ge=0, le=20, description="متوسط درجات الترم الأول (0-20)")
    sem2_enrolled: int = Field(ge=0, le=30)
    sem2_approved: int = Field(ge=0, le=30)
    sem2_grade: float = Field(ge=0, le=20)
    age_at_enrollment: int = Field(ge=15, le=80)
    tuition_up_to_date: bool
    scholarship_holder: bool

    @model_validator(mode="after")
    def approved_not_more_than_enrolled(self):
        if self.sem1_approved > self.sem1_enrolled:
            raise ValueError("sem1_approved can't be more than sem1_enrolled")
        if self.sem2_approved > self.sem2_enrolled:
            raise ValueError("sem2_approved can't be more than sem2_enrolled")
        return self
