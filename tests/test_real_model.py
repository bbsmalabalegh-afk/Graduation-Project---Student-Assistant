"""يتأكد إن موديل بسملة الحقيقي (student_model.pkl) بيتحمل ويدي نتايج منطقية.
محتاج xgboost متسطب — لو مش متسطب الاختبار بيتخطى."""
import os
import tempfile
import unittest

try:
    import xgboost  # noqa: F401
except ImportError as e:
    raise unittest.SkipTest(f"xgboost not installed: {e}")

os.environ.setdefault("SCALER_PATH", os.path.join(tempfile.mkdtemp(), "scaler.joblib"))

from backend.ml import predictor as ml  # noqa: E402
from tests.test_core import BAD, GOOD  # noqa: E402


class RealModelTests(unittest.TestCase):
    def test_real_model_loads_and_ranks(self):
        p = ml.load_predictor()
        good, bad = p.predict(GOOD), p.predict(BAD)
        print("GOOD:", good.to_dict())
        print("BAD :", bad.to_dict())
        self.assertAlmostEqual(sum(good.probabilities.values()), 1.0, places=2)
        self.assertLess(good.risk_probability, bad.risk_probability)
        self.assertEqual(bad.risk_level, "High")


if __name__ == "__main__":
    unittest.main()
