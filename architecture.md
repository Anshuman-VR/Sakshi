# Sakshi Architecture and Change Guide

This document is the practical map of the repository: what each part owns, how a decision travels through the system, and which files to edit for common changes.

## 1. System at a glance

Sakshi is a Flask application with a single-page dashboard and local Python modules. The dashboard calls the Flask API; the API coordinates the model gateway, the EZKL proof code, and the independent decision verifier. Decision receipts and Merkle witness batches are persisted as local JSON Lines files.

```text
Browser: dashboard/index.html
   |  POST /api/decide, GET /api/verify/:id, /api/stats, ...
   v
dashboard/app.py  (Flask routes / API boundary)
   |
   +--> gateway/gateway.py
   |      +--> gateway/registry.json       model contract, features, policy
   |      +--> gateway/adapters.py         ONNX inference adapter
   |      +--> gateway/explanations.py     optional SHAP explanations
   |      +--> zkproof/prove.py            per-decision EZKL proof
   |      +--> gateway/keys/               gateway signing keypair
   |      +--> gateway/decision_records.jsonl
   |      +--> gateway/merkle_witness.jsonl
   |
   +--> verifier/verifier.py               signed receipt / Merkle checks
   +--> zkproof/prove.py                   proof verification
   +--> models/evaluation_metrics.json     evaluation data for dashboard
```

The Borrower Portal submits an application and displays its receipt. The **LSP Model Console** is where the model owner inspects the registered model, features, evaluation metrics, and API integration. The **Bank Verification Portal** is for the lender/bank to check model integrity and verify decision evidence; it is not the owner-facing model configuration screen. The **Independent Decision Verifier** exposes receipt verification as a separate dashboard workflow, using the same backend verifier module.

These are separate dashboard views, not separate deployed services or authentication boundaries. The current Flask app serves all views and APIs from one process.

## 2. What happens during a decision

1. The browser submits the feature object and an optional numeric application ID to `POST /api/decide`.
2. `dashboard/app.py` performs basic request validation and calls `SakshiGateway.decide()`.
3. `gateway/gateway.py` loads the registered feature order and policy. It applies the configured minimum-age and maximum-amount checks, then prepares the ordered model input.
4. `gateway/adapters.py` runs the registered ONNX model through ONNX Runtime. It checks the model file SHA-256 against `gateway/registry.json` before inference and interprets the output according to the registered probability contract.
5. The gateway generates four random nonce values, requests an EZKL proof through `zkproof/prove.py`, and optionally gets SHAP values from `gateway/explanations.py`. SHAP is an optional explanation artifact, not the proof itself.
6. The gateway uses the proof's public probability as the canonical decision probability, applies the registered threshold, and constructs a decision record with model identity, input commitment, decision, probability/score, explanation, and proof metadata.
7. The gateway signs the decision payload with its RSA private key, hashes the payload, and appends the signed record to `gateway/decision_records.jsonl`.
8. Record hashes are accumulated into batches. When the batch reaches the configured size, or `/api/flush` is called, the gateway publishes a Merkle root and leaf list to `gateway/merkle_witness.jsonl`.
9. A verifier request checks the signed record and the associated evidence. The proof-specific endpoint checks the EZKL proof and proof artifact hash as well.

Policy rejects for the minimum-age or maximum-amount checks are recorded as signed policy-rejection receipts; they do not run the normal model/proof path.

## 3. Verification paths and API map

Routes are defined in `dashboard/app.py`.

| Endpoint | Purpose |
|---|---|
| `POST /api/decide` | Validate request and create a decision receipt |
| `GET /api/verify/<id>` | Flush pending Merkle leaves, then verify the decision receipt |
| `GET /api/zkproof/<id>` | Verify the EZKL proof and compare the proof file hash with the receipt |
| `GET /api/zkproof/file/<id>` | Download a proof artifact only when its SHA-256 matches the recorded proof hash |
| `GET /api/zkproof/public-settings` | Serve public EZKL settings |
| `GET /api/zkproof/verification-key` | Serve the public verification key |
| `GET /api/zkproof/srs` | Download the public SRS file |
| `GET /api/stats` | Return decision records for the active registered model |
| `GET /api/batches` | Return the count of published Merkle witness entries |
| `POST /api/flush` | Publish any pending Merkle batch |
| `GET /api/metrics` | Return model evaluation metrics JSON |
| `GET /api/model/verify` | Check model file presence/hash and presence of feature, threshold, and metrics configuration |
| `GET /api/registry` | Return registry metadata without the local ONNX path |

The proving key (`zkproof/keys/proving.key`) is not exposed by an API route. Keep private keys, proof-generation inputs/witnesses, and other secrets out of public endpoints and source control where appropriate.

## 4. File ownership: what to edit

### Dashboard and API

- **`dashboard/index.html`** — All dashboard HTML, CSS, browser-side JavaScript, portal names/copy, form fields, visible metrics, and frontend API calls live here. Change the visual design or the LSP-vs-bank portal wording here. Keep the roles clear: LSP owns/manages the model; bank/lender verifies it and checks receipts.
- **`dashboard/app.py`** — Flask routes, request validation, HTTP responses, endpoint wiring, file downloads, and server startup. Add/change API endpoints here. This file currently imports and coordinates the gateway and verifier; it contains no separate service deployment for each portal.
- **`run.py`** — Optional all-in-one launcher that trains/exports the baseline, runs EZKL setup, and then starts the dashboard. For simply restarting the existing dashboard, use `python3 dashboard/app.py` rather than rerunning setup unnecessarily.

### Model and feature contract

- **`models/train_model.py`** — Dataset loading, selected feature list/order, preprocessing/model training, evaluation, SHAP explainer creation, ONNX export, and writing the model registry. Edit this when changing the training pipeline, target mapping, features, model family, or ONNX graph generation.
- **`data/credit.csv`** — The local dataset used by the training script. Replace only with a dataset whose schema/target encoding has been deliberately mapped.
- **`data/DATASET.md`** — Dataset source, encoding notes, and limitations.
- **`models/sakshi_credit_v1.onnx`** — Exported inference artifact consumed at runtime. Normally regenerate it via `models/train_model.py`; do not edit the binary manually.
- **`models/evaluation_metrics.json`** — Generated evaluation report read by the dashboard. Regenerate it through the training script; do not hand-edit it to make model results look different.
- **`models/shap_explainer.pkl`** — Generated SHAP explainer/scaler artifact consumed by the optional explanation adapter. Regenerate with the training script if the model or features change.
- **`gateway/registry.json`** — Runtime contract for the active model: model name/version/path/hash, feature names and order, labels, output contract, policy thresholds, and proof-related metadata. The training script rewrites this file when it exports a model. If editing it manually, keep it consistent with the ONNX artifact and proof setup.
- **`gateway/adapters.py`** — Runtime ONNX loading, model-hash check, and probability-output interpretation. Edit this if adding a supported output contract or changing how registered ONNX outputs are read.
- **`gateway/explanations.py`** — Optional SHAP explanation adapter and mapping of values to feature labels. Edit this to change explanation behavior without changing the core receipt protocol.

### Evidence generation and verification

- **`gateway/gateway.py`** — Decision orchestration: policy checks, ordered feature vector, nonce generation, model inference, proof invocation, canonical decision, signed receipt, record persistence, and Merkle batching. Change the evidence creation flow here.
- **`verifier/verifier.py`** — Independent validation of a stored receipt: signature/hash consistency, Merkle inclusion evidence, proof binding and policy/decision consistency. Change this when the receipt format or verification rules change; update tests at the same time.
- **`gateway/keys/gateway_private.pem`** — Private signing key. Treat as secret and protect/back it up securely. Replacing it changes the trust root for newly signed receipts; old receipts need the corresponding public key to remain verifiable.
- **`gateway/keys/gateway_public.pem`** — Public half of the gateway signing keypair, used by verification. The gateway recreates it from the private key on startup.
- **`gateway/decision_records.jsonl`** — Append-only-in-practice local receipt log (one JSON record per line). This is runtime data, not source code. Avoid editing records manually except in controlled tamper tests.
- **`gateway/merkle_witness.jsonl`** — Published Merkle batch roots and leaves. This is runtime evidence data; do not edit it to repair a failed verification without understanding the evidence chain.

### Zero-knowledge proof setup

- **`zkproof/prove.py`** — Per-decision EZKL proof generation and proof verification helpers. Change this for proof input construction, public-instance decoding, or proof checks.
- **`zkproof/setup.py`** — Compiles/setup artifacts for the current ONNX circuit and generates proving/verification material. Rerun after changing the ONNX model, input shape, feature schema, or circuit-relevant configuration.
- **`zkproof/settings.json`** — Generated EZKL circuit/settings output. Treat as setup output, not a hand-maintained source of truth.
- **`zkproof/manifest.json`** — Proof-system metadata and setup smoke-test record. Keep it aligned with the model and proof statement when setup behavior changes.
- **`zkproof/compiled.ezkl`, `zkproof/kzg.srs`, `zkproof/keys/`** — Compiled circuit, SRS, and proof keys. These are generated setup artifacts. Never serve the proving key publicly. A model/circuit change may require regenerating all of them together.
- **`zkproof/proofs/` and `zkproof/tmp/`** — Per-decision proof artifacts and temporary prover/witness files. Runtime/generated data, not the place to implement behavior. Keep private inputs/witnesses protected.
- **`zkproof/README.md`** — Proof subsystem notes.

### Tests and dependencies

- **`tests/test_pipeline.py`** — Regression tests for the decision/evidence pipeline. Extend these when changing receipt fields, proof binding, verification behavior, or policy handling.
- **`requirements.txt`** — Python package dependencies and the pinned EZKL version.
- **`README.md`** — Project overview, quick start, dataset notes, and high-level architecture. Keep it aligned with this document when major architecture changes land.
- **`.gitignore`** — Git exclusion rules. Check this before adding generated artifacts, private keys, local data, or runtime evidence to the repository.

## 5. Common change recipes

### Change portal labels, layout, or frontend behavior
1. Edit `dashboard/index.html`.
2. If a new backend value is needed, add/adjust a route in `dashboard/app.py`.
3. Verify the correct owner sees model details in the LSP console and the bank portal remains focused on verification.

### Change the policy threshold or hard limits
1. Update `policy` in `gateway/registry.json` (`approve_threshold`, `max_credit_amount`, `min_age`).
2. Check that `gateway/gateway.py` and `verifier/verifier.py` apply/check the same semantics.
3. Add/update tests in `tests/test_pipeline.py` and verify existing receipts are interpreted as expected. A threshold change does not by itself retrain the model, but it changes decision semantics for new receipts.

### Change features, feature order, or the trained model
1. Update `models/train_model.py` and the feature definitions/encodings as required.
2. Run `python3 models/train_model.py` to regenerate the ONNX model, metrics, SHAP artifact, and registry.
3. Run `python3 zkproof/setup.py` to rebuild model-specific EZKL setup artifacts and keys.
4. Run the test suite and verify a fresh decision and receipt. Do not assume old proofs are compatible with the new model/setup.

### Change the receipt schema or cryptographic checks
1. Update receipt construction in `gateway/gateway.py`.
2. Update corresponding verification/reconstruction rules in `verifier/verifier.py` and any proof API handling in `dashboard/app.py`.
3. Update dashboard rendering in `dashboard/index.html` if new fields should be shown.
4. Add regression tests in `tests/test_pipeline.py` and verify both valid and tampered records.

### Change the proof statement or proof input/output contract
1. Inspect `models/train_model.py` (ONNX input/output shape), `gateway/registry.json`, `zkproof/prove.py`, and `zkproof/setup.py` together.
2. Regenerate setup artifacts with `python3 zkproof/setup.py` after the model/input contract changes.
3. Update `verifier/verifier.py`, `zkproof/manifest.json`, and tests to match the new statement.
4. Never claim the proof demonstrates fairness, data quality, or that the model is accurate. It establishes only the configured cryptographic statement and bindings that the verifier actually checks.

### Add or change an API endpoint
1. Add route and validation in `dashboard/app.py`.
2. Update frontend calls and display in `dashboard/index.html` if it is a dashboard feature.
3. Add tests for valid, invalid, missing, and tampered inputs as relevant.

## 6. Important boundaries and caveats

- The model is a Logistic Regression baseline trained on a historical UCI German Credit dataset; its data is not representative of Indian borrowers. Do not treat its outputs as production lending advice.
- The LSP, bank, borrower, and independent verifier are UI roles/concepts in this single Flask app. The current dashboard does not by itself provide authentication, authorization, or isolation between those roles.
- `/api/model/verify` checks that the registered model file exists and its hash matches the registry, and that selected metadata/configuration is present. It does **not** prove that the model is fair, unbiased, accurate, legally compliant, or independently audited.
- EZKL proof verification is not a proof of fairness or overall model quality. It verifies the configured relation between the private input commitment and public probability, subject to the implemented model/circuit and verifier checks.
- `gateway/decision_records.jsonl`, `gateway/merkle_witness.jsonl`, proof files, keys, SRS, and setup outputs are state/artifacts. Back them up and manage access deliberately; do not casually delete or hand-edit them to make the UI appear healthy.
- A change to model weights, feature order, ONNX input shape, or proof-relevant settings can invalidate the existing proof setup. Regenerate model and EZKL artifacts as one coordinated change.

## 7. Quick local checks

From the repository root:

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile dashboard/app.py gateway/gateway.py gateway/adapters.py gateway/explanations.py verifier/verifier.py zkproof/prove.py zkproof/setup.py models/train_model.py
```

Start only the dashboard/API with:

```bash
python3 dashboard/app.py
```

The default port is `9000`; override it with the `PORT` environment variable.
