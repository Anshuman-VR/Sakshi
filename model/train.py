import os
import sys
import pickle
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score

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
