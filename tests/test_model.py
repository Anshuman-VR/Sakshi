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
    assert os.path.getsize(onnx_path) > 200

    # 3. Model Commitment C
    c = compute_model_commitment()
    assert len(c) == 64  # SHA-256 hex string

    # 4. Parity Report
    report = generate_parity_report()
    assert report["decision_agreement_pct"] >= 98.0
    assert report["status"] == "PASS"

    # 5. Personas
    personas_path = os.path.join(os.path.dirname(__file__), "..", "model", "demo_personas.json")
    with open(personas_path, "r") as f:
        data = json.load(f)
    assert len(data["personas"]) >= 3
