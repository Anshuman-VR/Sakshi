# Sakshi — Model-Agnostic Decision Evidence Prototype

Sakshi is an evidence layer around model-driven decisions. It preserves a decision receipt, model identity, a privacy-preserving input commitment, an optional explanation, a cryptographic signature, and Merkle inclusion evidence without embedding one model architecture in the evidence protocol.

**Research prototype only.** The active model uses historical German credit data, not Indian borrowers. It is not a lending recommendation or fit for real credit decisions.

## Dataset

`data/credit.csv` is derived from the official [UCI Statlog German Credit Data](https://archive.ics.uci.edu/dataset/144/statloggermancreditdata), Hans Hofmann (1994), DOI [10.24432/C5NC77](https://doi.org/10.24432/C5NC77), CC BY 4.0. It contains 1,000 observations. Sakshi uses 11 selected predictors; `default=1` means source class 2 (bad credit risk), and `default=0` means source class 1 (good credit risk). Encodings and limitations are documented in `data/DATASET.md`.

## Quick start

Install dependencies in a virtual environment, then run:

```bash
python3 models/train_model.py
python3 zkproof/setup.py
python3 dashboard/app.py
```

Open `http://127.0.0.1:9000` (or set `PORT`). `python3 zkproof/setup.py` is model-specific and should be rerun whenever the ONNX model or feature schema changes. Keep proving keys, SRS, witnesses, private inputs, and per-decision proof files local.

## Architecture

- `gateway/adapters.py`: ONNX model adapter consumes a registered model through a probability output contract.
- `gateway/explanations.py`: optional SHAP adapter. Evidence creation does not require SHAP.
- `gateway/gateway.py`: model inference, proof-bound public input commitment and probability, policy check, optional explanation, signed record and Merkle batching.
- `verifier/verifier.py`: signature, record hash, Merkle inclusion, EZKL proof, input commitment, model hash, public probability and decision consistency checks.
- `zkproof/`: EZKL/Halo2 setup and per-decision proof integration.
- `models/evaluation_metrics.json`: stratified holdout and 5-fold cross-validation results.

## ZK proof statement

Sakshi uses EZKL/Halo2 with **hashed (Poseidon) input visibility** and a **public model probability output**. The raw feature vector is private to the prover. The proof exposes the Poseidon commitment to the quantized feature vector plus four random private nonce dimensions, and the model's quantized probability; the nonce is never stored in the receipt, making offline guessing of low-entropy feature vectors harder; the gateway stores both in the signed receipt and bases the decision on that proof output. The verifier checks the proof, proof-file hash, model hash, input commitment, public probability, and decision threshold consistency against the signed record.

EZKL uses fixed-point quantization. The gateway checks the proof output against ONNX Runtime within 0.002 tolerance. The signed receipt uses the proof's public probability as its canonical value. Model parameters are fixed into the model-specific circuit; rerun setup when changing the ONNX model.

## Model evaluation

A stratified 80/20 split with random state 42 is used, plus 5-fold stratified cross-validation. See `models/evaluation_metrics.json` for accuracy, balanced accuracy, precision/recall/F1 for the bad-risk class, ROC-AUC, average precision, Brier score and confusion matrices. These are results on a small historical benchmark only. The compact MVP uses ordinal encodings for several categorical variables, imposing ordering assumptions; a richer categorical model and calibration study are future work.

## Model agnosticism

The evidence protocol consumes a registered ONNX probability adapter and treats explanations as optional artifacts. The current training script produces a Logistic Regression baseline, but other ONNX models can be registered if they implement the configured output contract, have the same feature schema or a registered feature adapter, and are compatible with EZKL. Each model requires its own hash, proof setup and verification key. The dashboard exposes `/api/zkproof/file/<numeric-id>`, `/api/zkproof/public-settings`, `/api/zkproof/verification-key`, and `/api/zkproof/srs` for the proof artifact and public verification material; the proving key is never served.
