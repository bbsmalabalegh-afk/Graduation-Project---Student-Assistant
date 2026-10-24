"""Dashboard.  Run:  streamlit run app.py   (after python pipeline.py)"""
import sqlite3, pandas as pd, plotly.express as px, streamlit as st

st.set_page_config("Student Success Predictor", layout="wide")
con = sqlite3.connect("students.db")
df = pd.read_sql("SELECT * FROM predictions", con)
res = pd.read_sql("SELECT * FROM model_results", con)

st.title("Student Success Predictor")
cls = st.sidebar.multiselect("Class", sorted(df.class_name.unique()), default=sorted(df.class_name.unique()))
lvl = st.sidebar.multiselect("Risk level", ["High", "Medium", "Low"], default=["High", "Medium"])
f = df[df.class_name.isin(cls)]

c = st.columns(4)
c[0].metric("Students", len(f))
c[1].metric("High risk", int((f.risk_level == "High").sum()))
c[2].metric("Avg attendance", f"{f.attendance_pct.mean():.0f}%")
c[3].metric("Avg grade", f"{f.avg_grade.mean():.0f}")

a, b = st.columns(2)
order = {"risk_level": ["Low", "Medium", "High"]}
cmap = {"Low": "#2a9d8f", "Medium": "#e9c46a", "High": "#e76f51"}
a.plotly_chart(px.histogram(f, x="class_name", color="risk_level", barmode="group",
               category_orders=order, color_discrete_map=cmap, title="Risk by class"), use_container_width=True)
b.plotly_chart(px.scatter(f, x="attendance_pct", y="avg_grade", color="risk_level",
               category_orders=order, color_discrete_map=cmap, title="Attendance vs grade"), use_container_width=True)

st.subheader("Students who need support")
t = f[f.risk_level.isin(lvl)].sort_values("risk_prob", ascending=False)
st.dataframe(t[["student_id", "class_name", "risk_prob", "risk_level", "top_factor",
                "avg_grade", "attendance_pct", "homework_rate"]], use_container_width=True, hide_index=True)

st.subheader("Model comparison")
st.dataframe(res, hide_index=True)
