# Back-End — Student Success Prediction System
**المسؤول:** عبد الرحمن داود (Back-End & Integration) — FastAPI + SQLite + JWT

## التشغيل محليًا
```bash
pip install -r requirements.txt
python -m backend.seed --admin-email admin@univ.edu --admin-password "ChangeMe123" --demo
uvicorn backend.main:app --reload
```
- الموقع: http://127.0.0.1:8000/  (index / login / dashboard)
- توثيق وتجربة الـ APIs: http://127.0.0.1:8000/docs
- حساب تجريبي من `--demo`: `doctor@univ.edu` / `Doctor12345`

## هيكل الفولدر
```
backend/
  main.py            السيرفر + ربط الواجهات (Static) + CORS
  config.py          الإعدادات (Environment Variables)
  schema.sql         تصميم قاعدة البيانات (4 جداول)
  database.py        الاتصال وإنشاء الجداول
  security.py        Hash للباسورد (PBKDF2) + JWT
  deps.py            المستخدم الحالي + الصلاحيات (admin / doctor / student)
  schemas.py         Validation لكل المدخلات (Pydantic)
  services.py        كل الـ SQL
  routers/           auth.py  students.py  predictions.py
  ml/predictor.py    ربط موديل بسملة (student_model.pkl)
  seed.py            حسابات وبيانات تجريبية
tests/               test_core.py (منطق) + test_api.py (كل الـ Endpoints)
```

## الـ Endpoints
| Method | Path | مين يقدر | الوظيفة |
|---|---|---|---|
| POST | `/api/auth/register` | الكل | تسجيل حساب طالب |
| POST | `/api/auth/login` | الكل | دخول → `access_token` |
| GET | `/api/auth/me` | أي مستخدم | بيانات المستخدم الحالي |
| GET/POST | `/api/users` | admin | عرض/إنشاء مستخدمين (دكاترة) |
| GET/POST | `/api/students` | doctor, admin | جدول الطلاب (بحث `?search=` وفلترة `?risk_level=High`) / إضافة طالب |
| GET/PUT/DELETE | `/api/students/{id}` | doctor, admin | عرض/تعديل/حذف طالب |
| GET | `/api/students/me` | student | ملف الطالب المربوط بحسابه |
| POST/GET | `/api/students/{id}/records` | doctor, admin | إدخال/عرض درجات الطالب |
| POST | `/api/students/{id}/predict` | doctor, admin | تنبؤ لطالب (بدرجات جديدة في الـ body أو آخر درجات محفوظة) |
| GET | `/api/students/{id}/predictions` | staff / الطالب نفسه | سجل نتايج الطالب |
| POST | `/api/predict` | أي مستخدم | تنبؤ سريع (اللي بتستخدمه صفحة الـ Dashboard) |
| GET | `/api/dashboard/stats` | doctor, admin | أرقام جاهزة للرسومات |
| GET | `/api/model/info` | الكل | حالة الموديل والـ features |
| GET | `/api/health` | الكل | السيرفر شغال؟ |

كل Endpoint محمي محتاج Header: `Authorization: Bearer <access_token>`

### مدخلات الموديل (body بتاع predict / records)
```json
{
  "admission_grade": 130, "age_at_enrollment": 19,
  "sem1_enrolled": 6, "sem1_approved": 5, "sem1_grade": 12.5,
  "sem2_enrolled": 6, "sem2_approved": 4, "sem2_grade": 11.8,
  "tuition_up_to_date": true, "scholarship_holder": false
}
```
### شكل النتيجة
```json
{
  "predicted_class": "Graduate", "predicted_class_ar": "في الطريق للتخرج",
  "risk_probability": 0.08, "risk_percent": 8.0,
  "risk_level": "Low", "risk_level_ar": "خطر منخفض",
  "probabilities": {"Dropout": 0.08, "Enrolled": 0.12, "Graduate": 0.80},
  "reasons": ["..."]
}
```
- `risk_probability` = احتمال Dropout. High ≥ 60% ، Medium ≥ 30% ، ولو الموديل توقّع Enrolled (متأخر) أقل مستوى بيبقى Medium.

## من الواجهة (JavaScript)
`fronted/js/api.js` فيه كل الدوال جاهزة:
```js
await API.login(email, password);      // وبعدها Auth.save(...)
await API.predict(record);
await API.students("?risk_level=High");
await API.stats();
```

## النشر على Render
`render.yaml` جاهز: Build `pip install -r requirements.txt` — Start `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
حدد `ADMIN_EMAIL` و `ADMIN_PASSWORD` من لوحة Render. ملحوظة: SQLite على الخطة المجانية بيتمسح مع كل Deploy؛ للعرض النهائي يُفضّل PostgreSQL.
