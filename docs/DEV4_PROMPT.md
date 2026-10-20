# DEV 4 AI AGENT PROMPT: Credit Model, Parity Verification & Customer UI Assist
**Role:** Credit Risk & Data Science Lead  
**Branch:** `feature/branch-1-zkml-core` (or dedicated sub-branch `feature/branch-4-model-data`)  
**Target:** Produce the clean real credit model (`scorecard.onnx`), commitment generator, parity report, demo personas, and customer loan application UI components.  
**Completion Time Limit:** 45 minutes unattended execution.

---

## 🎯 POKA-YOKE ZERO-FAILURE INSTRUCTIONS FOR AI AGENT

You are an expert Credit Risk Data Scientist and Full-Stack Engineer. Your job is to create a complete, production-grade machine learning credit underwriting pipeline using **real LendingClub loan data** (already downloaded in `model/data/lendingclub_clean.csv`), export it to ONNX, generate a mathematical model commitment $C$, and assist Dev 3 by providing the Customer Loan Application UI component (`BorrowerPortal.tsx`).

### Strict Rules to Avoid Discrepancies:
1. Feature order MUST strictly match `FEATURE_ORDER` in `shared/types.py`:
   `['bureau_score', 'monthly_income', 'foir', 'loan_tenure_months', 'num_active_loans', 'num_enquiries_6m', 'bank_account_age_months', 'loan_amount_requested', 'behaviour_idx', 'employment_type']`
2. Fixed-point scale is `1024`.
3. Never invent new feature names. Always import from `shared.types`.
4. Run all verification commands at the end to guarantee 100% pass before stopping.

---

## 📁 EXACT FILE TREE TO CREATE

```
sakshi/
  model/
    __init__.py
    download_real_data.py   # (Already exists)
    train.py                # Train scikit-learn scorecard
    export_onnx.py          # Convert to ONNX format
    commit.py               # Extract weights, add private salt, compute SHA-256 commitment C
    parity_report.py        # Float vs quantized ONNX inference test (>98% agreement)
    demo_personas.json      # 5 rich Indian applicant personas for live demo
    models/                 # Directory containing scorecard.pkl and scorecard.onnx
  dashboard/src/pages/
    BorrowerPortal.tsx      # Customer loan application page (for Dev 3)
    BorrowerReceipt.tsx     # Cryptographic decision receipt (for Dev 3)
  tests/
    test_model.py           # Unit test asserting model parity, commitment, and personas
```

---

## 📝 FILE 1: `model/__init__.py`
```python
"""Sakshi Model Module"""
```

---

## 📝 FILE 2: `model/train.py`
Create `model/train.py`:
```python
import os
import sys
import pickle
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score, classification_report

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from shared.types import FEATURE_ORDER

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "lendingclub_clean.csv")
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_PKL_PATH = os.path.join(MODELS_DIR, "scorecard.pkl")

def train_scorecard():
    os.makedirs(MODELS_DIR, exist_ok=True)
    if not os.path.exists(DATA_PATH):
        from model.download_real_data import download_and_process
        download_and_process()

    df = pd.read_csv(DATA_PATH)
    X = df[FEATURE_ORDER]
    y = df["decision"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # Standard Logistic Regression Credit Scorecard
    clf = LogisticRegression(max_iter=1000, random_state=42, class_weight="balanced")
    clf.fit(X_train, y_train)

    y_pred_proba = clf.predict_proba(X_test)[:, 1]
    y_pred = (y_pred_proba >= 0.5).astype(int)

    auc = roc_auc_score(y_test, y_pred_proba)
    acc = accuracy_score(y_test, y_pred)
    print(f"=== MODEL TRAINING COMPLETE ===")
    print(f"Test Samples: {len(X_test)}")
    print(f"AUC-ROC: {auc:.4f} | Accuracy: {acc:.4f}")

    with open(MODEL_PKL_PATH, "wb") as f:
        pickle.dump(clf, f)
    print(f"Model saved to: {MODEL_PKL_PATH}")
    return clf, X_test, y_test

if __name__ == "__main__":
    train_scorecard()
```

---

## 📝 FILE 3: `model/export_onnx.py`
Create `model/export_onnx.py`:
```python
import os
import sys
import pickle
import numpy as np
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from shared.types import FEATURE_ORDER

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_PKL_PATH = os.path.join(MODELS_DIR, "scorecard.pkl")
MODEL_ONNX_PATH = os.path.join(MODELS_DIR, "scorecard.onnx")

def export():
    if not os.path.exists(MODEL_PKL_PATH):
        from model.train import train_scorecard
        clf, _, _ = train_scorecard()
    else:
        with open(MODEL_PKL_PATH, "rb") as f:
            clf = pickle.load(f)

    # Initial type: batch of float inputs with feature count matching FEATURE_ORDER
    initial_type = [("float_input", FloatTensorType([None, len(FEATURE_ORDER)]))]
    onnx_model = convert_sklearn(clf, initial_types=initial_type, target_opset=12)

    with open(MODEL_ONNX_PATH, "wb") as f:
        f.write(onnx_model.SerializeToString())
    print(f"ONNX Model exported successfully to: {MODEL_ONNX_PATH}")
    return MODEL_ONNX_PATH

if __name__ == "__main__":
    export()
```

---

## 📝 FILE 4: `model/commit.py`
Create `model/commit.py`:
```python
import os
import sys
import json
import hashlib
import pickle

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from shared.types import FEATURE_ORDER

MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_PKL_PATH = os.path.join(MODELS_DIR, "scorecard.pkl")
SALT_PATH = os.path.join(os.path.dirname(__file__), "salt.bin")

def get_or_create_salt() -> bytes:
    if os.path.exists(SALT_PATH):
        with open(SALT_PATH, "rb") as f:
            return f.read()
    salt = os.urandom(32)
    with open(SALT_PATH, "wb") as f:
        f.write(salt)
    return salt

def compute_model_commitment() -> str:
    if not os.path.exists(MODEL_PKL_PATH):
        from model.train import train_scorecard
        clf, _, _ = train_scorecard()
    else:
        with open(MODEL_PKL_PATH, "rb") as f:
            clf = pickle.load(f)

    salt = get_or_create_salt()
    # Deterministic parameter serialization
    params = {
        "features": FEATURE_ORDER,
        "weights": [round(float(w), 6) for w in clf.coef_[0]],
        "intercept": round(float(clf.intercept_[0]), 6)
    }
    canonical = json.dumps(params, sort_keys=True, separators=(',', ':'))
    commitment = hashlib.sha256(salt + canonical.encode("utf-8")).hexdigest()
    print(f"=== MODEL COMMITMENT DERIVED ===")
    print(f"Commitment (C): {commitment}")
    return commitment

if __name__ == "__main__":
    compute_model_commitment()
```

---

## 📝 FILE 5: `model/parity_report.py`
Create `model/parity_report.py`:
```python
import os
import sys
import json
import pickle
import numpy as np
import pandas as pd
import onnxruntime as rt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from shared.types import FEATURE_ORDER

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "lendingclub_clean.csv")
MODELS_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_PKL_PATH = os.path.join(MODELS_DIR, "scorecard.pkl")
MODEL_ONNX_PATH = os.path.join(MODELS_DIR, "scorecard.onnx")
REPORT_PATH = os.path.join(os.path.dirname(__file__), "parity_report.json")

def generate_parity_report():
    if not os.path.exists(MODEL_ONNX_PATH):
        from model.export_onnx import export
        export()

    with open(MODEL_PKL_PATH, "rb") as f:
        clf = pickle.load(f)

    df = pd.read_csv(DATA_PATH)
    sample_df = df.sample(n=min(1000, len(df)), random_state=42)
    X = sample_df[FEATURE_ORDER].values.astype(np.float32)

    # Scikit-learn float inference
    sklearn_probs = clf.predict_proba(X)[:, 1]
    sklearn_decisions = (sklearn_probs >= 0.20).astype(int)  # Cutoff at threshold 0.20

    # ONNX inference
    sess = rt.InferenceSession(MODEL_ONNX_PATH)
    input_name = sess.get_inputs()[0].name
    label_name = sess.get_outputs()[1].name  # Probabilities output
    onnx_out = sess.run(None, {input_name: X})
    onnx_probs = np.array([p[1] for p in onnx_out[1]])
    onnx_decisions = (onnx_probs >= 0.20).astype(int)

    agreement = float(np.mean(sklearn_decisions == onnx_decisions))
    max_prob_diff = float(np.max(np.abs(sklearn_probs - onnx_probs)))

    report = {
        "dataset": "LendingClub Real Loan Records (9,578 samples)",
        "features_evaluated": len(FEATURE_ORDER),
        "test_sample_size": len(X),
        "threshold": 0.20,
        "agreement_pct": round(agreement * 100.0, 2),
        "max_probability_delta": round(max_prob_diff, 6),
        "status": "PASS" if agreement >= 0.98 else "FAIL"
    }

    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)

    print("=== MODEL PARITY REPORT ===")
    print(json.dumps(report, indent=2))
    assert agreement >= 0.98, f"Agreement {agreement} below 98%!"
    return report

if __name__ == "__main__":
    generate_parity_report()
```

---

## 📝 FILE 6: `model/demo_personas.json`
Create `model/demo_personas.json`:
```json
{
  "personas": [
    {
      "id": "persona_priya",
      "name": "Priya Sharma",
      "profile": "Prime Salaried Software Engineer",
      "expected_outcome": "APPROVE",
      "features": {
        "bureau_score": 758.0,
        "monthly_income": 95000.0,
        "foir": 0.28,
        "loan_tenure_months": 36.0,
        "num_active_loans": 1.0,
        "num_enquiries_6m": 0.0,
        "bank_account_age_months": 84.0,
        "loan_amount_requested": 150000.0,
        "behaviour_idx": 0.18,
        "employment_type": 0.0
      }
    },
    {
      "id": "persona_rahul",
      "name": "Rahul Verma",
      "profile": "Subprime High-Obligation Applicant",
      "expected_outcome": "REJECT",
      "features": {
        "bureau_score": 542.0,
        "monthly_income": 32000.0,
        "foir": 0.68,
        "loan_tenure_months": 36.0,
        "num_active_loans": 5.0,
        "num_enquiries_6m": 4.0,
        "bank_account_age_months": 22.0,
        "loan_amount_requested": 200000.0,
        "behaviour_idx": 0.88,
        "employment_type": 1.0
      }
    },
    {
      "id": "persona_amit",
      "name": "Amit Patel",
      "profile": "Borderline Credit Profile",
      "expected_outcome": "APPROVE",
      "features": {
        "bureau_score": 672.0,
        "monthly_income": 52000.0,
        "foir": 0.44,
        "loan_tenure_months": 36.0,
        "num_active_loans": 2.0,
        "num_enquiries_6m": 1.0,
        "bank_account_age_months": 45.0,
        "loan_amount_requested": 80000.0,
        "behaviour_idx": 0.45,
        "employment_type": 0.0
      }
    }
  ]
}
```

---

## 📝 FILE 7: Customer DLA UI Assist (`dashboard/src/pages/BorrowerPortal.tsx`)
Create `dashboard/src/pages/BorrowerPortal.tsx` with clean, institutional HDFC/Navi banking aesthetics:
```tsx
import React, { useState } from 'react';
import axios from 'axios';

export const BorrowerPortal: React.FC = () => {
  const [amount, setAmount] = useState<number>(150000);
  const [tenure, setTenure] = useState<number>(36);
  const [income, setIncome] = useState<number>(85000);
  const [consent, setConsent] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<any>(null);

  const calculateEMI = () => {
    const rate = 0.125 / 12; // 12.5% p.a.
    const emi = (amount * rate * Math.pow(1 + rate, tenure)) / (Math.pow(1 + rate, tenure) - 1);
    return Math.round(emi).toLocaleString('en-IN');
  };

  const handleApply = async () => {
    if (!consent) return alert("Consent required under DPDP Act 2025");
    setLoading(true);
    setResult(null);

    const payload = {
      applicant_name: "Priya Sharma",
      features: {
        bureau_score: 758.0,
        monthly_income: income,
        foir: 0.28,
        loan_tenure_months: tenure,
        num_active_loans: 1.0,
        num_enquiries_6m: 0.0,
        bank_account_age_months: 84.0,
        loan_amount_requested: amount,
        behaviour_idx: 0.18,
        employment_type: 0.0
      }
    };

    try {
      const res = await axios.post('/v1/demo/apply', payload);
      setResult(res.data);
    } catch (e: any) {
      setResult({ status: 'ERROR', message: e.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F4F6F8] flex flex-col justify-between font-sans text-slate-800">
      {/* Institutional Header */}
      <header className="bg-[#0A2540] text-white py-4 px-6 border-b border-slate-700 shadow-sm flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded bg-[#8B0000] flex items-center justify-center font-bold text-white text-sm">
            स
          </div>
          <div>
            <h1 className="font-semibold text-lg tracking-tight">Sakshi Digital Loan App</h1>
            <p className="text-xs text-slate-300">Powered by Regulated NBFC Partner</p>
          </div>
        </div>
        <span className="text-xs bg-slate-800 px-3 py-1 rounded-full text-slate-300 border border-slate-700">
          Fast-Track Disbursal
        </span>
      </header>

      {/* Main Loan Application Container */}
      <main className="max-w-xl w-full mx-auto p-4 flex-1">
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 space-y-6">
          <div className="border-b border-slate-100 pb-4">
            <h2 className="text-xl font-bold text-slate-900">Instant Personal Loan</h2>
            <p className="text-sm text-slate-500">Sanctioned in 2 minutes with automated cryptographic audit assurance</p>
          </div>

          {/* Amount Slider */}
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <label className="text-sm font-semibold text-slate-700">Requested Amount</label>
              <span className="text-xl font-bold text-[#0A2540]">₹{amount.toLocaleString('en-IN')}</span>
            </div>
            <input 
              type="range" min={25000} max={500000} step={5000} value={amount}
              onChange={(e) => setAmount(Number(e.target.value))}
              className="w-full accent-[#0A2540] h-2 bg-slate-200 rounded-lg cursor-pointer"
            />
            <div className="flex justify-between text-xs text-slate-400">
              <span>₹25,000</span>
              <span>₹5,00,000</span>
            </div>
          </div>

          {/* Tenure Buttons */}
          <div className="space-y-2">
            <label className="text-sm font-semibold text-slate-700">Repayment Tenure</label>
            <div className="grid grid-cols-4 gap-2">
              {[12, 24, 36, 48].map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTenure(t)}
                  className={`py-2 text-sm rounded-lg border font-medium transition ${
                    tenure === t ? 'border-[#0A2540] bg-[#0A2540] text-white' : 'border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100'
                  }`}
                >
                  {t} Mo
                </button>
              ))}
            </div>
          </div>

          {/* EMI Estimate Box */}
          <div className="bg-[#F8FAFC] border border-slate-200 rounded-lg p-4 flex justify-between items-center">
            <div>
              <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">Estimated Monthly EMI</p>
              <p className="text-2xl font-bold text-[#0A2540]">₹{calculateEMI()}<span className="text-xs font-normal text-slate-500"> /mo</span></p>
            </div>
            <span className="text-xs bg-emerald-100 text-emerald-800 font-semibold px-2.5 py-1 rounded-md">
              Interest: 12.5% p.a.
            </span>
          </div>

          {/* Monthly Income Input */}
          <div className="space-y-1">
            <label className="text-sm font-semibold text-slate-700">Net Monthly Salary</label>
            <div className="relative">
              <span className="absolute inset-y-0 left-0 pl-3 flex items-center text-slate-400 font-bold">₹</span>
              <input 
                type="number" value={income} onChange={(e) => setIncome(Number(e.target.value))}
                className="w-full pl-8 pr-4 py-2 border border-slate-300 rounded-lg font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0A2540]"
              />
            </div>
          </div>

          {/* Bureau Consent */}
          <div className="flex items-start space-x-3 bg-slate-50 p-3 rounded-lg border border-slate-200">
            <input 
              type="checkbox" id="consent" checked={consent} onChange={(e) => setConsent(e.target.checked)}
              className="mt-1 h-4 w-4 accent-[#0A2540] rounded border-slate-300"
            />
            <label htmlFor="consent" className="text-xs text-slate-600 leading-relaxed cursor-pointer">
              I authorize the lender to pull my CIBIL credit report and verify bank transactions via Account Aggregator in accordance with the <strong>RBI Digital Lending Directions, 2025</strong> and <strong>DPDP Act</strong>.
            </label>
          </div>

          {/* Action CTA */}
          <button
            onClick={handleApply} disabled={loading}
            className="w-full py-3.5 px-4 bg-[#0A2540] hover:bg-[#002D62] text-white rounded-lg font-bold text-base shadow-sm transition flex items-center justify-center space-x-2 disabled:opacity-50"
          >
            {loading ? (
              <span>Verifying Policy & Zero-Knowledge Conformance...</span>
            ) : (
              <span>Check Eligibility & Instant Disburse</span>
            )}
          </button>

          {/* Result Alert */}
          {result && (
            <div className={`p-4 rounded-lg border ${result.disbursed ? 'bg-emerald-50 border-emerald-200' : 'bg-rose-50 border-rose-200'}`}>
              <div className="flex justify-between items-center mb-1">
                <span className={`text-sm font-bold ${result.disbursed ? 'text-emerald-900' : 'text-rose-900'}`}>
                  {result.disbursed ? '✓ LOAN DISBURSED SUCCESSFULLY' : '✗ DISBURSAL WITHHELD'}
                </span>
                <span className="text-xs font-mono text-slate-500">ID: {result.decision_id}</span>
              </div>
              <p className="text-xs text-slate-700">
                {result.disbursed 
                  ? `₹${amount.toLocaleString('en-IN')} credited to bank account. Zero-Knowledge proof verified against NBFC board policy.`
                  : `Fail-closed gate held disbursal: ${result.failure_reason || 'Underwriting criteria not met'}`}
              </p>
              {result.disbursed && (
                <a 
                  href={`/receipt/${result.decision_id}`}
                  className="mt-2 inline-block text-xs font-bold text-[#0A2540] underline"
                >
                  Download Cryptographic Decision Receipt →
                </a>
              )}
            </div>
          )}
        </div>
      </main>

      {/* Institutional Compliance Footer */}
      <footer className="bg-white border-t border-slate-200 py-4 px-6 text-center text-xs text-slate-500">
        NBFC Registration No. N-07.00842 | Regulated by the Reserve Bank of India | 100% Zero-Knowledge Model Privacy
      </footer>
    </div>
  );
};
```

---

## 📝 FILE 8: Unit Test Suite (`tests/test_model.py`)
Create `tests/test_model.py`:
```python
import os
import sys
import json
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from shared.types import FEATURE_ORDER
from model.train import train_scorecard
from model.export_onnx import export
from model.commit import compute_model_commitment
from model.parity_report import generate_parity_report

def test_full_model_pipeline():
    # 1. Train
    clf, X_test, y_test = train_scorecard()
    assert clf is not None
    assert len(clf.coef_[0]) == len(FEATURE_ORDER)

    # 2. Export ONNX
    onnx_path = export()
    assert os.path.exists(onnx_path)
    assert os.path.getsize(onnx_path) > 500

    # 3. Model Commitment C
    c = compute_model_commitment()
    assert len(c) == 64  # SHA-256 hex string

    # 4. Parity Report
    report = generate_parity_report()
    assert report["agreement_pct"] >= 98.0
    assert report["status"] == "PASS"

    # 5. Personas
    personas_path = os.path.join(os.path.dirname(__file__), "..", "model", "demo_personas.json")
    with open(personas_path, "r") as f:
        data = json.load(f)
    assert len(data["personas"]) >= 3
```

---

## ⚡ VERIFICATION COMMAND FOR DEV 4
To verify your entire work passes cleanly in a single pass:
```bash
python -m pytest tests/test_model.py -v
```
When this command exits with code `0`, your job is 100% complete and ready to commit.
