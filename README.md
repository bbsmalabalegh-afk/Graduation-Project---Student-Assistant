# Student Success Predictor
pip install -r requirements.txt
python pipeline.py        # builds students.db, trains models, saves predictions
streamlit run app.py      # opens the dashboard
Data is synthetic. To use real data, replace make_data() in pipeline.py with pd.read_csv("your_file.csv")
(columns: student_id, class_name, avg_grade, attendance_pct, homework_rate, grade_trend, absences, struggling).
