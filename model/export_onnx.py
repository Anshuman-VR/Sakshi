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
    os.makedirs(MODELS_DIR, exist_ok=True)
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
