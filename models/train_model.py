import os, json, hashlib, pickle
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, roc_auc_score
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType
import shap

DATA_PATH     = os.path.join(os.path.dirname(__file__), '..', 'data', 'credit.csv')
MODEL_DIR     = os.path.dirname(__file__)
REGISTRY_PATH = os.path.join(MODEL_DIR, '..', 'gateway', 'registry.json')
EXPLAINER_PATH = os.path.join(MODEL_DIR, 'shap_explainer.pkl')

FEATURE_LABELS = {
    'duration_months':   'Loan Duration',
    'credit_amount':     'Loan Amount',
    'installment_rate':  'EMI-to-Income Ratio',
    'present_residence': 'Residence Stability',
    'age':               'Age',
    'existing_credits':  'Existing Loans',
    'num_dependents':    'Dependents',
    'checking_account':  'Checking Account Balance',
    'credit_history':    'Repayment History',
    'employment_years':  'Employment Duration',
    'savings_account':   'Savings Balance',
}

def generate_synthetic_credit_data(n=2000, seed=42):
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        'duration_months':    rng.integers(6, 72, n),
        'credit_amount':      rng.integers(500, 50000, n),
        'installment_rate':   rng.integers(1, 4, n),
        'present_residence':  rng.integers(1, 4, n),
        'age':                rng.integers(19, 75, n),
        'existing_credits':   rng.integers(1, 4, n),
        'num_dependents':     rng.integers(1, 2, n),
        'checking_account':   rng.integers(0, 3, n),
        'credit_history':     rng.integers(0, 4, n),
        'employment_years':   rng.integers(0, 4, n),
        'savings_account':    rng.integers(0, 4, n),
    })
    risk_score = (
        df['credit_amount'] / 10000
        - df['checking_account'] * 0.5
        - df['employment_years'] * 0.3
        + df['duration_months'] / 60
        + rng.normal(0, 0.3, n)
    )
    df['default'] = (risk_score > risk_score.quantile(0.35)).astype(int)
    return df

try:
    df = pd.read_csv(DATA_PATH)
except FileNotFoundError:
    df = generate_synthetic_credit_data()
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    df.to_csv(DATA_PATH, index=False)

FEATURES = [c for c in df.columns if c != 'default']
X = df[FEATURES].values.astype(np.float32)
y = df['default'].values

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
pipeline = Pipeline([('scaler', StandardScaler()), ('clf', LogisticRegression(max_iter=1000, C=0.5, class_weight='balanced'))])
pipeline.fit(X_train, y_train)

# SHAP explainer on the scaled data
X_train_scaled = pipeline['scaler'].transform(X_train)
explainer = shap.LinearExplainer(pipeline['clf'], X_train_scaled, feature_perturbation='interventional')
with open(EXPLAINER_PATH, 'wb') as f:
    pickle.dump({'explainer': explainer, 'scaler': pipeline['scaler'], 'features': FEATURES, 'labels': FEATURE_LABELS}, f)
print(f"SHAP explainer saved → {EXPLAINER_PATH}")

# ONNX export
initial_type = [('float_input', FloatTensorType([None, len(FEATURES)]))]
onnx_model   = convert_sklearn(pipeline, initial_types=initial_type, target_opset=12)
onnx_path    = os.path.join(MODEL_DIR, 'sakshi_credit_v1.onnx')
with open(onnx_path, 'wb') as f:
    f.write(onnx_model.SerializeToString())

with open(onnx_path, 'rb') as f:
    model_hash = hashlib.sha256(f.read()).hexdigest()

registry = {
    "version": "1.0.0", "model_name": "sakshi_credit_v1",
    "onnx_path": os.path.abspath(onnx_path), "model_hash": model_hash,
    "features": FEATURES, "feature_labels": FEATURE_LABELS,
    "policy": {"approve_threshold": 0.45, "max_credit_amount": 50000, "min_age": 21},
    "registered_by": "lender_admin", "registered_at": "2026-10-14T00:00:00Z"
}
os.makedirs(os.path.dirname(REGISTRY_PATH), exist_ok=True)
with open(REGISTRY_PATH, 'w') as f:
    json.dump(registry, f, indent=2)
print(f"✅ Model + SHAP ready. Hash: {model_hash[:16]}…")
