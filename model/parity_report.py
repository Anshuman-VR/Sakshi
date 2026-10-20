"""Compare scikit-learn float inference with the exported ONNX Runtime graph."""
from __future__ import annotations

import json
import os
import pickle
import sys
from pathlib import Path

import numpy as np
import onnxruntime as rt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from shared.types import FEATURE_ORDER

DATA_PATH = ROOT / "model" / "data" / "lendingclub_clean.csv"
MODELS_DIR = ROOT / "model" / "models"
MODEL_PKL_PATH = MODELS_DIR / "scorecard.pkl"
MODEL_ONNX_PATH = MODELS_DIR / "scorecard.onnx"
REPORT_PATH = ROOT / "model" / "parity_report.json"
THRESHOLD = 0.20


def generate_parity_report() -> dict:
    if not DATA_PATH.is_file():
        from model.download_real_data import download_and_process
        download_and_process()
    if not MODEL_PKL_PATH.is_file():
        from model.train import train_scorecard
        train_scorecard()
    if not MODEL_ONNX_PATH.is_file():
        from model.export_onnx import export
        export()

    with MODEL_PKL_PATH.open("rb") as stream:
        clf = pickle.load(stream)
    df = pd.read_csv(DATA_PATH)
    sample_df = df.sample(n=min(1000, len(df)), random_state=42)
    X = sample_df[FEATURE_ORDER].to_numpy(dtype=np.float32)

    sklearn_probs = clf.predict_proba(X)[:, 1]
    session = rt.InferenceSession(str(MODEL_ONNX_PATH), providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    onnx_probs = np.asarray(session.run(None, {input_name: X})[0]).reshape(-1)
    if len(onnx_probs) != len(sklearn_probs):
        raise AssertionError("ONNX output row count does not match scikit-learn")

    sklearn_decisions = sklearn_probs >= THRESHOLD
    onnx_decisions = onnx_probs >= THRESHOLD
    agreement = float(np.mean(sklearn_decisions == onnx_decisions))
    max_prob_diff = float(np.max(np.abs(sklearn_probs - onnx_probs)))
    report = {
        "dataset": "LendingClub loan_data.csv source; 9,578 rows after feature mapping",
        "features_evaluated": len(FEATURE_ORDER),
        "test_sample_size": len(X),
        "threshold": THRESHOLD,
        "decision_agreement_pct": round(agreement * 100.0, 4),
        "max_probability_delta": round(max_prob_diff, 8),
        "comparison": "scikit-learn float32 input vs ONNX Runtime float32 output; not EZKL quantization parity",
        "status": "PASS" if agreement >= 0.98 else "FAIL",
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("=== MODEL / ONNX PARITY REPORT ===")
    print(json.dumps(report, indent=2))
    assert agreement >= 0.98, f"Decision agreement {agreement:.4%} below 98%"
    return report


if __name__ == "__main__":
    generate_parity_report()
