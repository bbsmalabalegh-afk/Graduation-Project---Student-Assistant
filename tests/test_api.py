"""اختبار الـ APIs كلها end-to-end بـ FastAPI TestClient.
تشغيل:  pip install -r requirements.txt pytest  ثم  python -m pytest tests -q
(بيستخدم موديل بديل عشان الاختبار ميعتمدش على xgboost)"""
import os
import tempfile

import unittest

try:
    import fastapi  # noqa: F401
    import httpx  # noqa: F401
    import pytest
except ImportError as e:  # لو المكتبات مش متسطبة الاختبار ده بيتخطى
    raise unittest.SkipTest(f"API tests need fastapi + httpx + pytest: {e}")

_tmp = tempfile.mkdtemp()
os.environ["DB_PATH"] = os.path.join(_tmp, "api_test.db")
os.environ["ADMIN_EMAIL"] = "admin@test.edu"
os.environ["ADMIN_PASSWORD"] = "AdminPass123"

from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402
from backend.ml import predictor as ml  # noqa: E402
from tests.test_core import BAD, GOOD, FakeModel, IdentityScaler  # noqa: E402


@pytest.fixture(scope="module")
def client():
    ml.set_predictor(ml.Predictor(FakeModel(), IdentityScaler(), version="fake"))
    with TestClient(app) as c:
        yield c
    ml.set_predictor(None)


def _login(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def test_full_flow(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/").status_code == 200            # الواجهة بتتعرض

    # تسجيل طالب + دخول
    r = client.post("/api/auth/register", json={"full_name": "Student One", "email": "s1@test.edu", "password": "Student123"})
    assert r.status_code == 201 and r.json()["role"] == "student"
    assert client.post("/api/auth/register", json={"full_name": "Student One", "email": "s1@test.edu", "password": "Student123"}).status_code == 409
    assert client.post("/api/auth/login", json={"email": "s1@test.edu", "password": "bad"}).status_code == 401
    student_h = _login(client, "s1@test.edu", "Student123")
    assert client.get("/api/auth/me", headers=student_h).json()["email"] == "s1@test.edu"

    # من غير توكن / طالب مش مسموح له بإدارة الطلاب
    assert client.get("/api/students").status_code == 401
    assert client.get("/api/students", headers=student_h).status_code == 403

    # الأدمن يعمل دكتور
    admin_h = _login(client, "admin@test.edu", "AdminPass123")
    r = client.post("/api/users", headers=admin_h, json={"full_name": "Dr House", "email": "dr@test.edu", "password": "Doctor123", "role": "doctor"})
    assert r.status_code == 201
    doc_h = _login(client, "dr@test.edu", "Doctor123")

    # الطالب يعمل تنبؤ سريع
    r = client.post("/api/predict", headers=student_h, json=GOOD)
    assert r.status_code == 200 and r.json()["risk_level"] == "Low"
    assert client.post("/api/predict", headers=student_h, json=dict(GOOD, sem1_grade=25)).status_code == 422
    assert client.post("/api/predict", headers=student_h, json=dict(GOOD, sem1_approved=9)).status_code == 422

    # الدكتور: طالب + درجات + تنبؤ
    sid = client.post("/api/students", headers=doc_h, json={"student_code": "2024001", "full_name": "Ali Hassan", "department": "CS", "level": 2}).json()["id"]
    assert client.post(f"/api/students/{sid}/predict", headers=doc_h).status_code == 404   # لسه مفيش درجات
    assert client.post(f"/api/students/{sid}/records", headers=doc_h, json=BAD).status_code == 201
    r = client.post(f"/api/students/{sid}/predict", headers=doc_h)
    assert r.status_code == 200 and r.json()["risk_level"] == "High"
    assert client.get(f"/api/students/{sid}/predictions", headers=doc_h).json()[0]["risk_level"] == "High"
    assert client.get(f"/api/students/{sid}/predictions", headers=student_h).status_code == 403
    assert client.get("/api/students?risk_level=High", headers=doc_h).json()[0]["id"] == sid
    stats = client.get("/api/dashboard/stats", headers=doc_h).json()
    assert stats["by_risk_level"]["High"] == 1

    assert client.put(f"/api/students/{sid}", headers=doc_h, json={"level": 3}).json()["level"] == 3
    assert client.delete(f"/api/students/{sid}", headers=doc_h).status_code == 204
    assert client.get(f"/api/students/{sid}", headers=doc_h).status_code == 404
