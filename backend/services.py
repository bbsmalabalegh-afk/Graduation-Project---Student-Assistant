"""منطق التعامل مع قاعدة البيانات (SQL) — منفصل عن الـ Routers عشان يبقى سهل نختبره ونغيّره."""
import json
import sqlite3

from .security import hash_password, verify_password


class NotFound(Exception):
    pass


class Conflict(Exception):
    pass


def _d(row):
    return dict(row) if row is not None else None


# ======================= Users =======================
USER_COLS = "id, full_name, email, role, is_active, created_at"


def create_user(con, full_name, email, password, role="student"):
    try:
        cur = con.execute(
            "INSERT INTO users (full_name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (full_name.strip(), email.strip().lower(), hash_password(password), role),
        )
        con.commit()
    except sqlite3.IntegrityError as e:
        raise Conflict("Email already registered") from e
    return get_user(con, cur.lastrowid)


def get_user(con, user_id):
    row = con.execute(f"SELECT {USER_COLS} FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        raise NotFound("User not found")
    return _d(row)


def list_users(con):
    return [_d(r) for r in con.execute(f"SELECT {USER_COLS} FROM users ORDER BY id")]


def authenticate(con, email, password):
    row = con.execute(
        f"SELECT {USER_COLS}, password_hash FROM users WHERE email = ?", (email.strip().lower(),)
    ).fetchone()
    if row is None or not row["is_active"] or not verify_password(password, row["password_hash"]):
        return None
    user = _d(row)
    user.pop("password_hash")
    return user


def ensure_admin(con, email, password, name="System Admin"):
    """يعمل أدمن لو مش موجود (بيتنادى وقت تشغيل السيرفر لو ADMIN_EMAIL متحدد)."""
    row = con.execute("SELECT id FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()
    if row is None:
        return create_user(con, name, email, password, role="admin")
    return get_user(con, row["id"])


# ======================= Students =======================
_STUDENT_SELECT = """
SELECT s.*,
       p.risk_probability AS latest_risk_probability,
       p.risk_level       AS latest_risk_level,
       p.predicted_class  AS latest_predicted_class,
       p.created_at       AS latest_prediction_at
FROM students s
LEFT JOIN predictions p ON p.id = (
    SELECT id FROM predictions WHERE student_id = s.id ORDER BY id DESC LIMIT 1
)
"""


def create_student(con, data: dict, created_by=None):
    try:
        cur = con.execute(
            "INSERT INTO students (student_code, full_name, email, department, level, created_by) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (data["student_code"].strip(), data["full_name"].strip(), data.get("email"),
             data.get("department"), data.get("level"), created_by),
        )
        con.commit()
    except sqlite3.IntegrityError as e:
        raise Conflict("Student code already exists") from e
    return get_student(con, cur.lastrowid)


def get_student(con, student_id):
    row = con.execute(_STUDENT_SELECT + " WHERE s.id = ?", (student_id,)).fetchone()
    if row is None:
        raise NotFound("Student not found")
    return _d(row)


def get_student_by_user(con, user_id):
    row = con.execute(_STUDENT_SELECT + " WHERE s.user_id = ?", (user_id,)).fetchone()
    return _d(row)


def list_students(con, search=None, risk_level=None, limit=100, offset=0):
    where, params = [], []
    if search:
        where.append("(s.full_name LIKE ? OR s.student_code LIKE ?)")
        params += [f"%{search}%", f"%{search}%"]
    if risk_level:
        where.append("p.risk_level = ?")
        params.append(risk_level)
    sql = _STUDENT_SELECT + (" WHERE " + " AND ".join(where) if where else "")
    sql += " ORDER BY s.id DESC LIMIT ? OFFSET ?"
    return [_d(r) for r in con.execute(sql, params + [limit, offset])]


def update_student(con, student_id, changes: dict):
    get_student(con, student_id)
    changes = {k: v for k, v in changes.items() if k in {"full_name", "email", "department", "level"}}
    if changes:
        sets = ", ".join(f"{k} = ?" for k in changes)
        con.execute(f"UPDATE students SET {sets} WHERE id = ?", (*changes.values(), student_id))
        con.commit()
    return get_student(con, student_id)


def delete_student(con, student_id):
    cur = con.execute("DELETE FROM students WHERE id = ?", (student_id,))
    con.commit()
    if cur.rowcount == 0:
        raise NotFound("Student not found")


# ======================= Academic records (grades) =======================
RECORD_FIELDS = ["admission_grade", "sem1_enrolled", "sem1_approved", "sem1_grade",
                 "sem2_enrolled", "sem2_approved", "sem2_grade", "age_at_enrollment",
                 "tuition_up_to_date", "scholarship_holder"]


def add_record(con, student_id, data: dict, created_by=None):
    get_student(con, student_id)
    values = [int(data[f]) if isinstance(data[f], bool) else data[f] for f in RECORD_FIELDS]
    cur = con.execute(
        f"INSERT INTO academic_records (student_id, {', '.join(RECORD_FIELDS)}, created_by) "
        f"VALUES (?, {', '.join('?' * len(RECORD_FIELDS))}, ?)",
        (student_id, *values, created_by),
    )
    con.commit()
    return get_record(con, cur.lastrowid)


def get_record(con, record_id):
    row = con.execute("SELECT * FROM academic_records WHERE id = ?", (record_id,)).fetchone()
    if row is None:
        raise NotFound("Record not found")
    return _record_out(row)


def _record_out(row):
    d = _d(row)
    d["tuition_up_to_date"] = bool(d["tuition_up_to_date"])
    d["scholarship_holder"] = bool(d["scholarship_holder"])
    return d


def list_records(con, student_id):
    get_student(con, student_id)
    rows = con.execute(
        "SELECT * FROM academic_records WHERE student_id = ? ORDER BY id DESC", (student_id,))
    return [_record_out(r) for r in rows]


def latest_record(con, student_id):
    get_student(con, student_id)
    row = con.execute(
        "SELECT * FROM academic_records WHERE student_id = ? ORDER BY id DESC LIMIT 1", (student_id,)
    ).fetchone()
    if row is None:
        raise NotFound("No academic record for this student yet")
    return _record_out(row)


# ======================= Predictions =======================
def save_prediction(con, result: dict, model_version, student_id=None, record_id=None, created_by=None):
    cur = con.execute(
        "INSERT INTO predictions (student_id, record_id, predicted_class, risk_probability, risk_level, "
        "probabilities, model_version, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (student_id, record_id, result["predicted_class"], result["risk_probability"],
         result["risk_level"], json.dumps(result["probabilities"]), model_version, created_by),
    )
    con.commit()
    return cur.lastrowid


def list_predictions(con, student_id):
    get_student(con, student_id)
    rows = con.execute(
        "SELECT * FROM predictions WHERE student_id = ? ORDER BY id DESC", (student_id,)).fetchall()
    out = []
    for r in rows:
        d = _d(r)
        d["probabilities"] = json.loads(d["probabilities"])
        out.append(d)
    return out


# ======================= Dashboard stats (لرسومات أحمد) =======================
def dashboard_stats(con):
    total = con.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    latest = """
        SELECT p.* FROM predictions p
        WHERE p.student_id IS NOT NULL
          AND p.id = (SELECT MAX(id) FROM predictions WHERE student_id = p.student_id)
    """
    by_level = {"High": 0, "Medium": 0, "Low": 0}
    for r in con.execute(f"SELECT risk_level, COUNT(*) c FROM ({latest}) GROUP BY risk_level"):
        by_level[r["risk_level"]] = r["c"]
    by_class = {r["predicted_class"]: r["c"] for r in con.execute(
        f"SELECT predicted_class, COUNT(*) c FROM ({latest}) GROUP BY predicted_class")}
    by_dept = [_d(r) for r in con.execute(f"""
        SELECT COALESCE(s.department, 'غير محدد') AS department,
               COUNT(*) AS students,
               SUM(CASE WHEN l.risk_level = 'High' THEN 1 ELSE 0 END) AS high_risk,
               ROUND(AVG(l.risk_probability), 3) AS avg_risk
        FROM students s JOIN ({latest}) l ON l.student_id = s.id
        GROUP BY COALESCE(s.department, 'غير محدد') ORDER BY high_risk DESC""")]
    avg = con.execute(f"SELECT AVG(risk_probability) FROM ({latest})").fetchone()[0]
    return {
        "total_students": total,
        "assessed_students": sum(by_level.values()),
        "by_risk_level": by_level,
        "by_predicted_class": by_class,
        "by_department": by_dept,
        "average_risk": round(avg, 3) if avg is not None else None,
    }
