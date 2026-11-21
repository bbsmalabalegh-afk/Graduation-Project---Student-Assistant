"""إنشاء حسابات أولية للتجربة.
    python -m backend.seed --admin-email admin@univ.edu --admin-password "StrongPass123"
    python -m backend.seed --demo     # + دكتور تجريبي و 3 طلاب بدرجات (من غير تنبؤ)
"""
import argparse

from . import services
from .database import connect, init_db

DEMO_STUDENTS = [
    ("20210001", "أحمد محمد", "Computer Science", 3,
     dict(admission_grade=150, sem1_enrolled=6, sem1_approved=6, sem1_grade=14.5, sem2_enrolled=6,
          sem2_approved=6, sem2_grade=15.0, age_at_enrollment=18, tuition_up_to_date=True, scholarship_holder=True)),
    ("20210002", "سارة علي", "Information Systems", 2,
     dict(admission_grade=120, sem1_enrolled=6, sem1_approved=4, sem1_grade=11.0, sem2_enrolled=6,
          sem2_approved=3, sem2_grade=10.2, age_at_enrollment=20, tuition_up_to_date=True, scholarship_holder=False)),
    ("20210003", "محمود حسن", "Computer Science", 2,
     dict(admission_grade=105, sem1_enrolled=6, sem1_approved=1, sem1_grade=6.0, sem2_enrolled=6,
          sem2_approved=0, sem2_grade=0.0, age_at_enrollment=27, tuition_up_to_date=False, scholarship_holder=False)),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--admin-email")
    ap.add_argument("--admin-password")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    init_db()
    con = connect()
    if a.admin_email and a.admin_password:
        print("admin:", services.ensure_admin(con, a.admin_email, a.admin_password)["email"])
    if a.demo:
        try:
            doc = services.create_user(con, "Dr. Demo", "doctor@univ.edu", "Doctor12345", role="doctor")
            print("doctor: doctor@univ.edu / Doctor12345  (غيّرها بعد التجربة)")
        except services.Conflict:
            doc = None
        for code, name, dept, level, rec in DEMO_STUDENTS:
            try:
                s = services.create_student(con, dict(student_code=code, full_name=name, department=dept, level=level),
                                            created_by=doc and doc["id"])
                services.add_record(con, s["id"], rec)
                print("student:", code, name)
            except services.Conflict:
                pass
    con.close()


if __name__ == "__main__":
    main()
