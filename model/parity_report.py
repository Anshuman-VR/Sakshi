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
    # Handle dict of probabilities from onnx zipmap or tensor
    if isinstance(onnx_out[1], list) and isinstance(onnx_out[1][0], dict):
        onnx_probs = np.array([p[1] for p in onnx_out[1]])
    else:
        onnx_probs = np.array(onnx_out[1])[:, 1]
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
