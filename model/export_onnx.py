"""Export the trained binary logistic scorecard as EZKL-compatible ONNX ops.

skl2onnx's default LinearClassifier/ZipMap operators are not supported by the
current EZKL compiler. The model is a binary LogisticRegression, so the same
probability is exactly represented as sigmoid(X @ coef + intercept).
"""
from __future__ import annotations

import os
import pickle
import sys
from pathlib import Path

import numpy as np
import onnx
from onnx import TensorProto, helper, numpy_helper

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from shared.types import FEATURE_ORDER

MODELS_DIR = Path(__file__).resolve().parent / "models"
MODEL_PKL_PATH = MODELS_DIR / "scorecard.pkl"
MODEL_ONNX_PATH = MODELS_DIR / "scorecard.onnx"


def export() -> str:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    if not MODEL_PKL_PATH.is_file():
        from model.train import train_scorecard
        train_scorecard()

    with MODEL_PKL_PATH.open("rb") as stream:
        clf = pickle.load(stream)
    if len(clf.classes_) != 2 or list(clf.classes_) != [0, 1]:
        raise ValueError("EZKL scorecard export expects binary LogisticRegression classes [0, 1]")
    if np.asarray(clf.coef_).shape != (1, len(FEATURE_ORDER)):
        raise ValueError("trained model coefficient shape does not match shared FEATURE_ORDER")

    # ONNX inference input is a batch of rows in the canonical shared feature order.
    coef = np.asarray(clf.coef_[0], dtype=np.float32).reshape(len(FEATURE_ORDER), 1)
    intercept = np.asarray(clf.intercept_, dtype=np.float32).reshape(1)
    input_info = helper.make_tensor_value_info(
        "float_input", TensorProto.FLOAT, [None, len(FEATURE_ORDER)]
    )
    output_info = helper.make_tensor_value_info("probability", TensorProto.FLOAT, [None, 1])
    graph = helper.make_graph(
        nodes=[
            helper.make_node("MatMul", ["float_input", "coef"], ["linear"]),
            helper.make_node("Add", ["linear", "intercept"], ["logit"]),
            helper.make_node("Sigmoid", ["logit"], ["probability"]),
        ],
        name="sakshi_logistic_scorecard",
        inputs=[input_info],
        outputs=[output_info],
        initializer=[
            numpy_helper.from_array(coef, name="coef"),
            numpy_helper.from_array(intercept, name="intercept"),
        ],
    )
    model = helper.make_model(
        graph,
        opset_imports=[helper.make_opsetid("", 13)],
        producer_name="sakshi-ezkl-compatible-scorecard",
    )
    # EZKL 23.0.5 supports ONNX IR v9; newer ONNX libraries default to newer IRs.
    model.ir_version = 9
    onnx.checker.check_model(model)
    onnx.save(model, MODEL_ONNX_PATH)
    print(f"EZKL-compatible ONNX scorecard exported to: {MODEL_ONNX_PATH}")
    return str(MODEL_ONNX_PATH)


if __name__ == "__main__":
    export()
