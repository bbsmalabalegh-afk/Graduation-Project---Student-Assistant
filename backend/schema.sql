-- قاعدة بيانات نظام التنبؤ بالتعثر الأكاديمي
-- SQL عادي، يشتغل على SQLite ومعظمه يتنقل لـ PostgreSQL/MySQL بتعديلات بسيطة
-- (INTEGER PRIMARY KEY AUTOINCREMENT  ->  SERIAL في PostgreSQL / AUTO_INCREMENT في MySQL)

-- المستخدمين: admin / doctor / student
CREATE TABLE IF NOT EXISTS users (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name      TEXT    NOT NULL,
    email          TEXT    NOT NULL UNIQUE,
    password_hash  TEXT    NOT NULL,
    role           TEXT    NOT NULL DEFAULT 'student'
                   CHECK (role IN ('admin', 'doctor', 'student')),
    is_active      INTEGER NOT NULL DEFAULT 1,
    created_at     TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- الطلاب (جدول الطلاب اللي بتعرضه الواجهة)
CREATE TABLE IF NOT EXISTS students (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    student_code   TEXT    NOT NULL UNIQUE,          -- الرقم الجامعي
    full_name      TEXT    NOT NULL,
    email          TEXT,
    department     TEXT,
    level          INTEGER,
    user_id        INTEGER REFERENCES users(id) ON DELETE SET NULL,   -- حساب الطالب لو عنده
    created_by     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at     TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- السجل الأكاديمي / الدرجات (نفس مدخلات موديل بسملة)
CREATE TABLE IF NOT EXISTS academic_records (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id          INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    admission_grade     REAL    NOT NULL,   -- 0..200
    sem1_enrolled       INTEGER NOT NULL,
    sem1_approved       INTEGER NOT NULL,
    sem1_grade          REAL    NOT NULL,   -- 0..20
    sem2_enrolled       INTEGER NOT NULL,
    sem2_approved       INTEGER NOT NULL,
    sem2_grade          REAL    NOT NULL,   -- 0..20
    age_at_enrollment   INTEGER NOT NULL,
    tuition_up_to_date  INTEGER NOT NULL CHECK (tuition_up_to_date IN (0, 1)),
    scholarship_holder  INTEGER NOT NULL CHECK (scholarship_holder IN (0, 1)),
    created_by          INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at          TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- نتايج الـ AI (بنخزنها عشان لوحة التحكم والرسومات بتاعة أحمد)
CREATE TABLE IF NOT EXISTS predictions (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id        INTEGER REFERENCES students(id) ON DELETE CASCADE,  -- NULL لو تنبؤ سريع من غير طالب
    record_id         INTEGER REFERENCES academic_records(id) ON DELETE SET NULL,
    predicted_class   TEXT    NOT NULL,     -- Dropout / Enrolled / Graduate
    risk_probability  REAL    NOT NULL,     -- احتمال التعثر (Dropout) من 0 لـ 1
    risk_level        TEXT    NOT NULL CHECK (risk_level IN ('High', 'Medium', 'Low')),
    probabilities     TEXT    NOT NULL,     -- JSON بكل الاحتمالات
    model_version     TEXT,
    created_by        INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at        TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_records_student     ON academic_records(student_id);
CREATE INDEX IF NOT EXISTS idx_predictions_student ON predictions(student_id);
