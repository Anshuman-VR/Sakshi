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
