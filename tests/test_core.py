"""اختبارات للـ DB + الأمان + طبقة الموديل (من غير FastAPI ومن غير xgboost).
تشغيل:  python -m pytest tests -q     أو     python -m unittest discover tests
"""
import os
import tempfile
import unittest

import numpy as np
import pandas as pd

from backend import services
from backend.database import connect, init_db
from backend.ml import predictor as ml
from backend.security import create_access_token, decode_access_token, hash_password, verify_password

GOOD = dict(admission_grade=150, sem1_enrolled=6, sem1_approved=6, sem1_grade=14.5, sem2_enrolled=6,
            sem2_approved=6, sem2_grade=15.0, age_at_enrollment=18, tuition_up_to_date=True, scholarship_holder=True)
BAD = dict(admission_grade=100, sem1_enrolled=6, sem1_approved=1, sem1_grade=5.0, sem2_enrolled=6,
           sem2_approved=0, sem2_grade=0.0, age_at_enrollment=28, tuition_up_to_date=False, scholarship_holder=False)


class FakeModel:
    """موديل بديل: كل ما الـ Approved_Ratio يقل، احتمال Dropout يزيد."""
    def predict_proba(self, Z):
        ratio_z = Z[0][3]
        p_drop = 1 / (1 + np.exp(3 * ratio_z))
        return np.array([[p_drop, (1 - p_drop) * 0.3, (1 - p_drop) * 0.7]])


class IdentityScaler:
    def transform(self, X):
        X = np.asarray(X, dtype=float).copy()
        X[:, 3] = (X[:, 3] - 0.7) / 0.3
        return X


class SecurityTests(unittest.TestCase):
    def test_password_hash(self):
        h = hash_password("Secret123")
        self.assertNotIn("Secret123", h)
        self.assertTrue(verify_password("Secret123", h))
        self.assertFalse(verify_password("wrong", h))
        self.assertFalse(verify_password("x", "garbage"))

    def test_token_roundtrip(self):
        t = create_access_token(7, "doctor")
        p = decode_access_token(t)
        self.assertEqual(p["sub"], "7")
        self.assertEqual(p["role"], "doctor")


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "t.db")
        init_db(self.db)
        self.con = connect(self.db)

    def tearDown(self):
        self.con.close()
        self.tmp.cleanup()

    def test_users_and_login(self):
        u = services.create_user(self.con, "Dr Test", "Doc@Univ.edu", "Password1", "doctor")
        self.assertEqual(u["email"], "doc@univ.edu")
        with self.assertRaises(services.Conflict):
            services.create_user(self.con, "Dup", "doc@univ.edu", "Password1")
        self.assertIsNotNone(services.authenticate(self.con, "DOC@univ.edu", "Password1"))
        self.assertIsNone(services.authenticate(self.con, "doc@univ.edu", "nope"))

    def test_students_records_predictions_stats(self):
        s = services.create_student(self.con, dict(student_code="1", full_name="Ali Hassan", department="CS"))
        with self.assertRaises(services.Conflict):
            services.create_student(self.con, dict(student_code="1", full_name="Other One"))
        with self.assertRaises(services.NotFound):
            services.latest_record(self.con, s["id"])
        r = services.add_record(self.con, s["id"], BAD)
        self.assertIs(r["tuition_up_to_date"], False)
        self.assertEqual(services.latest_record(self.con, s["id"])["id"], r["id"])

        p = ml.Predictor(FakeModel(), IdentityScaler(), version="fake")
        res = p.predict(r).to_dict()
        self.assertEqual(res["risk_level"], "High")
        self.assertTrue(res["reasons"])
        services.save_prediction(self.con, res, "fake", student_id=s["id"], record_id=r["id"])

        listed = services.list_students(self.con, risk_level="High")
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["latest_risk_level"], "High")
        stats = services.dashboard_stats(self.con)
        self.assertEqual(stats["by_risk_level"]["High"], 1)
        self.assertEqual(stats["assessed_students"], 1)

        services.update_student(self.con, s["id"], {"level": 3, "student_code": "hack"})
        self.assertEqual(services.get_student(self.con, s["id"])["level"], 3)
        self.assertEqual(services.get_student(self.con, s["id"])["student_code"], "1")
        services.delete_student(self.con, s["id"])
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM predictions").fetchone()[0], 0)


class PredictorTests(unittest.TestCase):
    def test_feature_engineering_matches_training_script(self):
        X = ml.record_to_frame(GOOD)
        self.assertEqual(list(X.columns), ml.MODEL_FEATURES)
        self.assertAlmostEqual(X["Average_Grade"][0], 14.75)
        self.assertEqual(X["Total_Approved"][0], 12)
        self.assertAlmostEqual(X["Approved_Ratio"][0], 1.0, places=4)

    def test_levels(self):
        self.assertEqual(ml.risk_level_for(0.8), "High")
        self.assertEqual(ml.risk_level_for(0.4), "Medium")
        self.assertEqual(ml.risk_level_for(0.1), "Low")

    def test_good_vs_bad(self):
        p = ml.Predictor(FakeModel(), IdentityScaler())
        self.assertLess(p.predict(GOOD).risk_probability, p.predict(BAD).risk_probability)
        self.assertEqual(p.predict(GOOD).risk_level, "Low")


if __name__ == "__main__":
    unittest.main()
