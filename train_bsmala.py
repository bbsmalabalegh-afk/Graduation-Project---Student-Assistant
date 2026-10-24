import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score
import joblib
from xgboost import XGBClassifier

# ==========================================
# 1. Load and Advanced Feature Engineering
# ==========================================
df = pd.read_csv('data/train.csv')

# Create smart aggregated features for maximum predictive power
df['Average_Grade'] = (df['Curricular units 1st sem (grade)'] + df['Curricular units 2nd sem (grade)']) / 2
df['Total_Approved'] = df['Curricular units 1st sem (approved)'] + df['Curricular units 2nd sem (approved)']
df['Approved_Ratio'] = df['Total_Approved'] / (df['Curricular units 1st sem (enrolled)'] + df['Curricular units 2nd sem (enrolled)'] + 1e-5)

# Select high-impact feature set
features = [
    'Admission grade', 
    'Average_Grade',
    'Total_Approved',
    'Approved_Ratio',
    'Curricular units 1st sem (grade)',
    'Curricular units 2nd sem (grade)',
    'Age at enrollment',
    'Tuition fees up to date',
    'Scholarship holder'
]

X = df[features]
y = df['Target']

# Convert text labels into numeric codes (0, 1, 2)
y = y.astype('category').cat.codes

# Handle missing values securely
X.fillna(X.mean(numeric_only=True), inplace=True)

# Scale features for optimal model performance
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# ==========================================
# 2. Train-Test Split & XGBoost Elite Training
# ==========================================
X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)

# Initialize and train XGBoost with optimized hyperparameters
model = XGBClassifier(
    n_estimators=500, 
    learning_rate=0.03, 
    max_depth=7, 
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42
)
model.fit(X_train, y_train)

# ==========================================
# 3. Model Evaluation & Export
# ==========================================
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"🚀 High-Performance XGBoost Accuracy: {accuracy * 100:.2f}%")

# Save the elite model for Abdelrahman's backend integration
joblib.dump(model, 'student_model.pkl')
print("Model successfully saved as 'student_model.pkl'!")