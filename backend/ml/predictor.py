"""ربط موديل بسملة (student_model.pkl — XGBoost) بالسيرفر.

ملاحظات مهمة عن الموديل:
1) train_bsmala.py بيعمل StandardScaler على البيانات قبل التدريب، بس بيحفظ الموديل لوحده
   من غير الـ scaler. عشان كده هنا بنعيد بناء نفس الـ scaler بالظبط من data/train.csv
   (نفس الـ features ونفس الخطوات) ونحفظه في backend/ml/scaler.joblib لأول مرة.
2) الـ Target اتحول لأرقام بـ astype('category').cat.codes يعني ترتيب أبجدي:
   0 = Dropout (متعثر/منسحب) ، 1 = Enrolled (لسه مقيد) ، 2 = Graduate (هيتخرج)
3) "نسبة خطر التعثر" = احتمال الكلاس Dropout.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass

import joblib
import numpy as np
import pandas as pd

from .. import config

# نفس ترتيب الأعمدة في train_bsmala.py بالظبط (الترتيب مهم للموديل)
MODEL_FEATURES = [
    "Admission grade",
    "Average_Grade",
    "Total_Approved",
    "Approved_Ratio",
    "Curricular units 1st sem (grade)",
    "Curricular units 2nd sem (grade)",
    "Age at enrollment",
    "Tuition fees up to date",
    "Scholarship holder",
]
CLASS_LABELS = ["Dropout", "Enrolled", "Graduate"]
CLASS_LABELS_AR = {"Dropout": "معرض للتعثر/الانسحاب", "Enrolled": "مستمر لكن متأخر", "Graduate": "في الطريق للتخرج"}
RISK_LEVEL_AR = {"High": "خطر مرتفع", "Medium": "خطر متوسط", "Low": "خطر منخفض"}

HIGH_THRESHOLD = 0.60
MEDIUM_THRESHOLD = 0.30


def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """نفس الـ Feature Engineering اللي في train_bsmala.py."""
    df = df.copy()
    df["Average_Grade"] = (df["Curricular units 1st sem (grade)"] + df["Curricular units 2nd sem (grade)"]) / 2
    df["Total_Approved"] = df["Curricular units 1st sem (approved)"] + df["Curricular units 2nd sem (approved)"]
    df["Approved_Ratio"] = df["Total_Approved"] / (
        df["Curricular units 1st sem (enrolled)"] + df["Curricular units 2nd sem (enrolled)"] + 1e-5
    )
    return df


def record_to_frame(rec: dict) -> pd.DataFrame:
    """يحوّل مدخلات الـ API (أسماء snake_case) لنفس أعمدة الداتا سِت."""
    raw = pd.DataFrame([{
        "Admission grade": float(rec["admission_grade"]),
        "Curricular units 1st sem (enrolled)": float(rec["sem1_enrolled"]),
        "Curricular units 1st sem (approved)": float(rec["sem1_approved"]),
        "Curricular units 1st sem (grade)": float(rec["sem1_grade"]),
        "Curricular units 2nd sem (enrolled)": float(rec["sem2_enrolled"]),
        "Curricular units 2nd sem (approved)": float(rec["sem2_approved"]),
        "Curricular units 2nd sem (grade)": float(rec["sem2_grade"]),
        "Age at enrollment": float(rec["age_at_enrollment"]),
        "Tuition fees up to date": float(int(bool(rec["tuition_up_to_date"]))),
        "Scholarship holder": float(int(bool(rec["scholarship_holder"]))),
    }])
    return add_engineered_features(raw)[MODEL_FEATURES]


def build_scaler_from_training_data(train_csv=None):
    """يعيد بناء الـ StandardScaler بنفس خطوات train_bsmala.py."""
    from sklearn.preprocessing import StandardScaler

    df = add_engineered_features(pd.read_csv(train_csv or config.TRAIN_CSV))
    X = df[MODEL_FEATURES]
    X = X.fillna(X.mean(numeric_only=True))
    return StandardScaler().fit(X)


def risk_level_for(p: float) -> str:
    if p >= HIGH_THRESHOLD:
        return "High"
    if p >= MEDIUM_THRESHOLD:
        return "Medium"
    return "Low"


def explain(rec: dict) -> list[str]:
    """أسباب بسيطة ومفهومة للمستخدم (Rule-based) جنب نتيجة الموديل."""
    reasons = []
    enrolled = rec["sem1_enrolled"] + rec["sem2_enrolled"]
    approved = rec["sem1_approved"] + rec["sem2_approved"]
    if enrolled > 0 and approved / enrolled < 0.6:
        reasons.append("نسبة المواد اللي نجح فيها أقل من 60% من المواد المسجلة.")
    if (rec["sem1_grade"] + rec["sem2_grade"]) / 2 < 10:
        reasons.append("متوسط درجات الترمين أقل من 10 من 20.")
    elif rec["sem2_grade"] < rec["sem1_grade"] - 2:
        reasons.append("درجات الترم التاني نزلت بشكل واضح عن الترم الأول.")
    if not rec["tuition_up_to_date"]:
        reasons.append("المصروفات الدراسية مش متسددة — ده من أقوى المؤشرات على الانسحاب.")
    if rec["admission_grade"] < 110:
        reasons.append("درجة القبول منخفضة نسبيًا.")
    return reasons


@dataclass
class PredictionResult:
    predicted_class: str
    risk_probability: float
    risk_level: str
    probabilities: dict
    reasons: list

    def to_dict(self) -> dict:
        return {
            "predicted_class": self.predicted_class,
            "predicted_class_ar": CLASS_LABELS_AR[self.predicted_class],
            "risk_probability": self.risk_probability,
            "risk_percent": round(self.risk_probability * 100, 1),
            "risk_level": self.risk_level,
            "risk_level_ar": RISK_LEVEL_AR[self.risk_level],
            "probabilities": self.probabilities,
            "reasons": self.reasons,
        }


class Predictor:
    def __init__(self, model, scaler, version: str = "xgboost-bsmala-v1"):
        self.model = model
        self.scaler = scaler
        self.version = version

    def predict(self, rec: dict) -> PredictionResult:
        X = record_to_frame(rec)
        Z = self.scaler.transform(X)
        proba = np.asarray(self.model.predict_proba(Z))[0]
        probs = {label: round(float(p), 4) for label, p in zip(CLASS_LABELS, proba)}
        predicted = CLASS_LABELS[int(np.argmax(proba))]
        risk = probs["Dropout"]
        level = risk_level_for(risk)
        # الطالب اللي الموديل شايفه "Enrolled" يعني متأخر عن التخرج في ميعاده = تعثر جزئي
        if predicted == "Enrolled" and level == "Low":
            level = "Medium"
        return PredictionResult(predicted, risk, level, probs, explain(rec))


# ---------- تحميل كسول (Lazy) مرة واحدة للسيرفر كله ----------
_lock = threading.Lock()
_predictor: Predictor | None = None
_load_error: str | None = None


def load_predictor() -> Predictor:
    model = joblib.load(config.MODEL_PATH)  # محتاج مكتبة xgboost متسطبة
    if config.SCALER_PATH.exists():
        scaler = joblib.load(config.SCALER_PATH)
    else:
        scaler = build_scaler_from_training_data()
        config.SCALER_PATH.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(scaler, config.SCALER_PATH)
    return Predictor(model, scaler)


def get_predictor() -> Predictor:
    """بترجع الموديل أو بترمي RuntimeError برسالة واضحة لو مش عارف يحمّله."""
    global _predictor, _load_error
    if _predictor is None:
        with _lock:
            if _predictor is None:
                try:
                    _predictor = load_predictor()
                    _load_error = None
                except Exception as e:  # noqa: BLE001
                    _load_error = f"{type(e).__name__}: {e}"
                    raise RuntimeError("AI model is not available: " + _load_error) from e
    return _predictor


def set_predictor(p: Predictor | None) -> None:
    """للاختبارات: نحط موديل بديل."""
    global _predictor
    _predictor = p


def model_status() -> dict:
    return {
        "loaded": _predictor is not None,
        "version": _predictor.version if _predictor else None,
        "error": _load_error,
        "features": MODEL_FEATURES,
        "classes": CLASS_LABELS,
        "thresholds": {"high": HIGH_THRESHOLD, "medium": MEDIUM_THRESHOLD},
    }
