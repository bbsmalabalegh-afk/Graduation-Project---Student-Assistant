"""Step 1: build the DB, Step 2: train models, Step 3: save predictions.
Run:  python pipeline.py
Replace make_data() with your real CSV/Excel to use real data."""
import os, sqlite3, joblib, numpy as np, pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, recall_score, f1_score

DB = "students.db"
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model.joblib")
FEATURES = ["avg_grade", "attendance_pct", "homework_rate", "grade_trend", "absences"]
LABELS = {"avg_grade": "Low grades", "attendance_pct": "Low attendance",
          "homework_rate": "Missed homework", "grade_trend": "Declining grades",
          "absences": "Many absences"}

def make_data(n=600, seed=42):
    r = np.random.default_rng(seed)
    ability = r.normal(0, 1, n)
    df = pd.DataFrame({
        "student_id": range(1, n + 1),
        "class_name": r.choice(["1A", "1B", "2A", "2B", "3A"], n),
        "avg_grade": np.clip(68 + 12 * ability + r.normal(0, 6, n), 20, 100),
        "attendance_pct": np.clip(88 + 7 * ability + r.normal(0, 6, n), 40, 100),
        "homework_rate": np.clip(80 + 12 * ability + r.normal(0, 10, n), 10, 100),
        "grade_trend": np.round(3 * ability + r.normal(0, 4, n), 1),
    })
    df["absences"] = np.round((100 - df.attendance_pct) * 0.9).astype(int)
    risk = (-0.07 * (df.avg_grade - 60) - 0.05 * (df.attendance_pct - 80)
            - 0.03 * (df.homework_rate - 70) - 0.08 * df.grade_trend + r.normal(0, 0.8, n))
    df["struggling"] = (risk > np.quantile(risk, 0.75)).astype(int)
    return df

def main():
    con = sqlite3.connect(DB)
    make_data().to_sql("students", con, if_exists="replace", index=False)
    # SQL step: read the features from the database
    df = pd.read_sql("SELECT * FROM students", con)
    X, y = df[FEATURES], df["struggling"]
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, stratify=y, random_state=1)
    sc = StandardScaler().fit(Xtr)
    models = {
        "Logistic Regression": (LogisticRegression(class_weight="balanced", max_iter=1000), True),
        "Random Forest": (RandomForestClassifier(300, class_weight="balanced", random_state=1), False),
    }
    rows, fitted = [], {}
    for name, (m, scaled) in models.items():
        m.fit(sc.transform(Xtr) if scaled else Xtr, ytr)
        p = m.predict(sc.transform(Xte) if scaled else Xte)
        rows.append({"model": name, "accuracy": accuracy_score(yte, p),
                     "recall": recall_score(yte, p), "f1": f1_score(yte, p)})
        fitted[name] = m
    res = pd.DataFrame(rows).round(3)
    print(res.to_string(index=False))
    best = res.sort_values("recall", ascending=False).iloc[0]["model"]  # recall matters most
    print("Best model (by recall):", best)

    # Final predictions + top contributing factor per student (logistic model)
    lr = fitted["Logistic Regression"]
    Z = sc.transform(X)
    joblib.dump({"model": lr, "scaler": sc, "features": FEATURES, "labels": LABELS}, MODEL_PATH)  # used by student_app.py
    df["risk_prob"] = fitted[best].predict_proba(Z if best == "Logistic Regression" else X)[:, 1].round(3)
    df["risk_level"] = pd.cut(df.risk_prob, [-1, .33, .66, 2], labels=["Low", "Medium", "High"])
    contrib = Z * lr.coef_[0]
    df["top_factor"] = [LABELS[FEATURES[i]] for i in contrib.argmax(axis=1)]
    df.to_sql("predictions", con, if_exists="replace", index=False)
    res.to_sql("model_results", con, if_exists="replace", index=False)
    con.close()
    print("Saved to", DB)

if __name__ == "__main__":
    main()
