"""Student-facing page: the student enters his data and sees his risk.
Run:  python -m streamlit run student_app.py   (after python pipeline.py)"""
import os, joblib, pandas as pd, streamlit as st

st.set_page_config("احسب نسبة خطر التعثر", page_icon="🎓")
st.markdown("<style>.stApp{direction:rtl;text-align:right}</style>", unsafe_allow_html=True)

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model.joblib")
if not os.path.exists(path):
    st.error("النموذج مش جاهز. شغّل الأول: python pipeline.py")
    st.stop()
art = joblib.load(path)
model, scaler, FEATURES = art["model"], art["scaler"], art["features"]

ADVICE = {
    "avg_grade": "راجع المواد الضعيفة واطلب مساعدة المدرس أو مجموعة مذاكرة.",
    "attendance_pct": "حاول تنتظم في الحضور، الغياب المتكرر من أكبر أسباب التعثر.",
    "homework_rate": "التزم بتسليم الواجبات في مواعيدها، حتى لو مش كاملة.",
    "grade_trend": "درجاتك بتنزل، اتكلم مع مدرسك بدري قبل ما الفرق يكبر.",
    "absences": "قلل أيام الغياب قدر الإمكان.",
}
TREND = {"بتتحسن": 4.0, "ثابتة تقريبًا": 0.0, "بتنزل": -4.0}

st.title("🎓 احسب نسبة خطر التعثر")
st.caption("اكتب بياناتك الحالية، وهتشوف احتمال إنك تحتاج دعم دراسي.")

with st.form("f"):
    grade = st.slider("متوسط درجاتك (من 100)", 0, 100, 70)
    att = st.slider("نسبة حضورك %", 0, 100, 85)
    hw = st.slider("نسبة الواجبات اللي سلّمتها %", 0, 100, 75)
    trend = st.radio("درجاتك في آخر الاختبارات", list(TREND), index=1, horizontal=True)
    go = st.form_submit_button("احسب نسبة الخطر", use_container_width=True)

if go:
    row = pd.DataFrame([{"avg_grade": grade, "attendance_pct": att, "homework_rate": hw,
                         "grade_trend": TREND[trend], "absences": round((100 - att) * 0.9)}])[FEATURES]
    z = scaler.transform(row)
    p = float(model.predict_proba(z)[0, 1])
    contrib = dict(zip(FEATURES, (z * model.coef_[0])[0]))

    st.divider()
    st.metric("نسبة خطر التعثر", f"{p:.0%}")
    st.progress(min(max(p, 0.0), 1.0))
    if p > 0.66:
        st.error("خطر مرتفع: يُفضّل تتواصل مع مدرسك أو المرشد الدراسي في أقرب وقت.")
    elif p > 0.33:
        st.warning("خطر متوسط: لسه الوقت متاح تحسّن وضعك.")
    else:
        st.success("خطر منخفض: كمّل على نفس المستوى.")

    reasons = [k for k, v in sorted(contrib.items(), key=lambda x: -x[1]) if v > 0.3 and k != "absences"]
    if reasons:
        st.subheader("إيه اللي بيرفع الخطر؟")
        for k in reasons[:3]:
            st.write("• " + ADVICE[k])
    st.caption("النتيجة تقدير إحصائي من نموذج تعلّم آلة وليست حكمًا نهائيًا.")
