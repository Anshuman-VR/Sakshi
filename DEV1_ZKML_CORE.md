# DEV 1: ZK/ML Core - Complete Technical Specification

## Role & Ownership
Dev 1 owns everything inside the LSP Zone. You build:
1. The synthetic India-style credit dataset and model training pipeline
2. EZKL circuit compilation and proof generation
3. The LSP prover sidecar (FastAPI service)
4. Policy document structure and signing tools

## Repository Structure (your branch)
```
sakshi/
  shared/          # READ-ONLY after hour 2 - shared contracts
  model/
    generate_data.py     # synthetic dataset generation
    train.py             # model training (LR + XGBoost)
    export_onnx.py       # ONNX export with skl2onnx
    commit.py            # generate commitment C from model
    parity_report.py     # float vs quantized accuracy comparison
    models/              # saved model artifacts (gitignored in prod)
    data/                # synthetic dataset (gitignored in prod)
  circuits/
    compile.py           # EZKL compile + setup + calibrate
    prove.py             # generate proof for a witness
    verify_local.py      # local verification test
    artifacts/           # ezkl compiled artifacts (gitignored - large)
    settings.json        # EZKL settings template
  sidecar/
    main.py              # FastAPI app entrypoint
    ingestor.py          # consume decision events from HTTP or queue
    witness_builder.py   # build EZKL witness from features
    prover_worker.py     # async worker: prove + upload
    outbox.py            # SQLite outbox for at-least-once delivery
    uploader.py          # POST proof to Lender Node
    models.py            # SQLAlchemy models for sidecar
    config.py            # settings from env vars
    requirements.txt
    Dockerfile
  policy/
    schema.py            # policy document dataclass / pydantic model
    sign.py              # Ed25519 sign a policy doc
    verify_policy.py     # verify dual signatures
    example_policy.json  # example policy for demo
  tests/
    test_model.py        # parity report assertions
    test_circuit.py      # prove + verify round-trip test
    test_sidecar.py      # sidecar API tests (httpx)
    test_policy.py       # policy signing tests
    conftest.py          # shared fixtures
```

## Shared Contracts (you must implement to this spec exactly)
Import from `shared/types.py`:
```python
from shared.types import (
    DecisionEvent,        # input you receive from LSP decision system
    ProofPayload,         # what you POST to Lender Node /v1/proofs
    DecisionNotice,       # what you POST to Lender Node /v1/decisions
    ModelRegistration,    # what you POST to Lender Node /v1/models
    PolicyDocument,       # the signed policy you load at startup
    JobStatus,            # QUEUED, PROVING, UPLOADED, VERIFIED, FAILED
)
```

Define these exact Pydantic models in shared/types.py:
```python
from pydantic import BaseModel
from typing import Literal, Optional, Dict, Any
from datetime import datetime

class DecisionEvent(BaseModel):
    decision_id: str          # e.g. "d_8842"
    application_id: str       # e.g. "a_5531"
    policy_id: str            # e.g. "pol_nbfc42_lspX_personal_v3"
    features: Dict[str, float] # raw features (stays in LSP zone)
    decision: int              # 1=approve, 0=reject
    ts: str                    # ISO 8601 timestamp

class DecisionNotice(BaseModel):
    decision_id: str
    application_id_hash: str   # SHA-256 hex of application_id
    policy_id: str
    decision: int
    ts: str

class ProofPayload(BaseModel):
    decision_id: str
    policy_id: str
    proof: str                 # base64 encoded EZKL proof bytes
    public_inputs: Dict[str, Any]  # {policy_hash, C, X, decision, threshold, epoch}

class ModelRegistration(BaseModel):
    commitment: str            # SHA-256 hex of serialized model weights
    circuit_hash: str          # SHA-256 hex of EZKL compiled circuit
    vk: str                    # base64 encoded verification key
    feature_schema_hash: str   # SHA-256 hex of feature schema JSON
    parity_report: Dict[str, Any]  # {float_auc, quantized_auc, agreement_pct}
    lsp_sig: str               # Ed25519 signature (hex)
    lsp_pubkey: str            # Ed25519 public key (hex)

class PolicyDocument(BaseModel):
    policy_id: str
    version: int
    lender_id: str
    lsp_id: str
    product: str
    model_commitment: str      # C
    circuit_hash: str
    feature_schema_hash: str
    decision_threshold: float  # e.g. 0.200
    fixed_point_scale: int     # e.g. 1024
    hard_rules: list           # list of rule dicts
    proof_sla_minutes: int     # e.g. 10
    valid_from: str            # ISO 8601
    valid_to: str              # ISO 8601
    lsp_sig: str               # Ed25519 sig over canonical JSON
    lender_sig: str            # Ed25519 sig over canonical JSON
    lsp_pubkey: str
    lender_pubkey: str

class VerificationResult(BaseModel):
    verification_id: str
    decision_id: str
    status: Literal['VERIFIED', 'FAILED', 'PENDING']
    reason: Optional[str]      # e.g. MODEL_MISMATCH, THRESHOLD_MISMATCH, REPLAY, INVALID_PROOF
    verified_at: Optional[str]
    ledger_seq: Optional[int]

class LedgerEntry(BaseModel):
    seq: int
    decision_id: str
    verification_id: str
    status: str
    reason: Optional[str]
    policy_id: str
    model_commitment: str
    proof_hash: str
    ts: str
    prev_hash: str
    row_hash: str

class JobStatus(BaseModel):
    job_id: str
    decision_id: str
    status: Literal['QUEUED', 'PROVING', 'UPLOADED', 'VERIFIED', 'FAILED']
    error: Optional[str] = None
    created_at: str
    updated_at: str
```

## Sidecar API Specification (you implement this)

Base URL: http://sidecar:8001 (internal to lsp_net)

```
POST /v1/prove
  Request: DecisionEvent
  Response: 202 { job_id: str, status: 'QUEUED' }

GET /v1/jobs/{job_id}
  Response: JobStatus

GET /healthz
  Response: 200 { status: 'ok', version: str }

GET /metrics
  Response: Prometheus text format with:
    - sakshi_proofs_total{status='...'}
    - sakshi_proof_duration_seconds (histogram)
    - sakshi_queue_depth
    - sakshi_outbox_pending
```

## What You POST to the Lender Node

The Lender Node is at: http://lender-node:8000 (or LENDER_NODE_URL env var)
Auth: Header `X-Sakshi-Key: {SIDECAR_API_KEY}` (env var)

Flow:
1. Decision arrives -> POST DecisionNotice to /v1/decisions (starts SLA clock)
2. Proof generated -> POST ProofPayload to /v1/proofs

## Model Training Specification

### Synthetic Dataset (generate_data.py)
Generate 10,000 samples with these features:
```python
features = {
    'bureau_score': randint(300, 900),       # CIBIL-style score
    'monthly_income': lognormal(10.5, 0.5), # INR, roughly 15k-200k
    'foir': uniform(0.1, 0.85),              # Fixed Obligation to Income Ratio
    'loan_tenure_months': choice([12,24,36,48,60]),
    'num_active_loans': randint(0, 8),
    'num_enquiries_6m': randint(0, 15),
    'bank_account_age_months': randint(1, 240),
    'loan_amount_requested': lognormal(11.5, 0.6),  # INR 50k - 3L
    'behaviour_idx': uniform(0, 1),          # synthetic behavioural signal
    'employment_type': choice([0,1,2]),      # 0=salaried, 1=self-employed, 2=other
}
# Target: approve if bureau_score > 650 AND foir < 0.55 AND score > threshold
# Add noise to make it realistic
```

### Model Tier 1: Logistic Regression Scorecard
- 8-10 features
- Binned where appropriate (bureau_score binned into 6 buckets)
- Train with scikit-learn LogisticRegression
- Target AUC > 0.75 on held-out test set
- Export to ONNX via skl2onnx

### Model Tier 2: XGBoost (Stretch - attempt only if Tier 1 proves cleanly)
- max_depth=3, n_estimators=30
- Same feature set
- Export to ONNX via onnxmltools

### Model Commitment (commit.py)
```python
import hashlib, json, numpy as np

def compute_model_commitment(model, salt: bytes) -> str:
    # Serialize model params deterministically
    params = extract_model_params(model)  # weights, biases as float list
    canonical = json.dumps(params, sort_keys=True, separators=(',', ':'))
    payload = salt + canonical.encode('utf-8')
    return hashlib.sha256(payload).hexdigest()
```
Store salt in a file (salt.bin) - never committed to git, never sent anywhere.

### EZKL Circuit Compilation (compile.py)
```python
import ezkl
# Standard EZKL workflow:
# 1. ezkl.gen_settings(model_path, settings_path)
# 2. ezkl.calibrate_settings(data_path, model_path, settings_path, target='resources')
# 3. ezkl.compile_circuit(model_path, compiled_path, settings_path)
# 4. ezkl.setup(compiled_path, vk_path, pk_path)
# This is SLOW (minutes). Run once and cache.

def get_circuit_hash(compiled_path: str) -> str:
    with open(compiled_path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()
```

### Proof Generation (prove.py)
```python
import ezkl, json, base64

def generate_proof(features: dict, compiled_path, pk_path, settings_path) -> tuple[str, dict]:
    # 1. Build witness input
    input_data = [[features[k] for k in FEATURE_ORDER]]
    witness_input = {'input_data': input_data}

    # 2. Generate witness
    ezkl.gen_witness(witness_input_json, compiled_path, witness_path)

    # 3. Generate proof
    ezkl.prove(witness_path, compiled_path, pk_path, proof_path, 'single')

    # 4. Read proof
    with open(proof_path, 'rb') as f:
        proof_bytes = f.read()
    proof_b64 = base64.b64encode(proof_bytes).decode()

    # 5. Compute public inputs for Lender Node
    public_inputs = {
        'C': model_commitment,      # from commit.py
        'X': compute_input_hash(features),  # SHA-256 of canonical features
        'decision': decision,
        'threshold': policy.decision_threshold,
        'policy_hash': compute_policy_hash(policy),
        'epoch': int(datetime.now().strftime('%Y%m%d'))
    }
    return proof_b64, public_inputs

def compute_input_hash(features: dict) -> str:
    canonical = json.dumps(features, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode()).hexdigest()
```

## Sidecar Implementation

### config.py
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    lender_node_url: str = 'http://lender-node:8000'
    sidecar_api_key: str  # shared secret for auth to lender node
    policy_id: str = 'pol_nbfc42_lspX_personal_v3'
    policy_path: str = '/app/policy/active_policy.json'
    compiled_circuit_path: str = '/app/circuits/artifacts/model.compiled'
    pk_path: str = '/app/circuits/artifacts/pk.key'
    salt_path: str = '/app/model/salt.bin'
    db_path: str = '/app/data/sidecar.db'
    num_workers: int = 2
    proof_sla_minutes: int = 10

    class Config:
        env_prefix = 'SAKSHI_SIDECAR_'
```

### outbox.py (SQLite outbox for at-least-once delivery)
```python
# Table: outbox
# id | decision_id | payload_type | payload_json | status | attempts | created_at | next_retry_at
# Outbox ensures: if the process crashes after generating proof but before uploading,
# it retries on restart. This is the transactional outbox pattern.
```

### prover_worker.py
```python
# Worker loop:
# 1. Pop QUEUED job from in-memory queue
# 2. Set status PROVING in DB
# 3. Call prove.py -> get proof_b64 + public_inputs
# 4. Write to outbox (status=PENDING_UPLOAD)
# 5. Set status UPLOADED in job DB
# 6. Upload loop (with retry):
#    a. POST DecisionNotice to /v1/decisions
#    b. POST ProofPayload to /v1/proofs
#    c. If success: mark outbox DONE
#    d. If fail: increment attempts, set next_retry_at (exponential backoff)
```

## Tests

### test_circuit.py - THE MOST IMPORTANT TEST
```python
def test_honest_proof_verifies():
    # 1. Generate a valid proof
    # 2. Verify locally with EZKL
    # Assert: verification passes

def test_tamper_model_commitment_fails():
    # 1. Generate valid proof
    # 2. Change the commitment C in public inputs
    # Assert: verification fails (wrong public inputs)

def test_tamper_threshold_fails():
    # 1. Generate valid proof
    # 2. Claim threshold=0.05 (lower than real 0.20)
    # Assert: public inputs mismatch detected

def test_replay_detection():
    # Sidecar should track seen proof hashes
    # Assert: submitting same proof twice returns an error or is idempotent

def test_parity_report():
    # Assert: float vs ONNX quantized model agree on > 98% of test samples
```

### test_sidecar.py
```python
import httpx, pytest
from fastapi.testclient import TestClient

def test_health():
    # GET /healthz -> 200

def test_submit_decision_event():
    # POST /v1/prove with valid DecisionEvent
    # Assert: 202, job_id returned

def test_job_status():
    # After submitting, GET /v1/jobs/{job_id}
    # Assert: status in QUEUED|PROVING|UPLOADED|FAILED

def test_invalid_features_rejected():
    # POST /v1/prove with missing features
    # Assert: 422
```

## Docker Setup

### Dockerfile (sidecar)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "sidecar.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

### requirements.txt (sidecar)
```
ezkl==10.4.0  # pin version!
scikit-learn==1.5.0
xgboost==2.0.3
onnx==1.16.0
skl2onnx==1.17.0
numpy==1.26.4
fastapi==0.111.0
uvicorn[standard]==0.30.1
httpx==0.27.0
sqlalchemy==2.0.30
aiosqlite==0.20.0
cryptography==42.0.8
pydantic==2.7.1
pydantic-settings==2.3.0
```

## Environment Variables
```env
# .env.sidecar (do NOT commit)
SAKSHI_SIDECAR_LENDER_NODE_URL=http://lender-node:8000
SAKSHI_SIDECAR_SIDECAR_API_KEY=dev-shared-secret-change-in-prod
SAKSHI_SIDECAR_POLICY_ID=pol_demo_v1
SAKSHI_SIDECAR_NUM_WORKERS=2
```

## Build Stages (your personal checklist)

### Stage 1: Dataset + Model (Hour 0-3)
- [ ] generate_data.py produces 10k synthetic Indian credit records
- [ ] train.py trains LR scorecard, AUC > 0.75
- [ ] export_onnx.py exports model.onnx
- [ ] parity_report.py shows >98% float/quantized agreement
- [ ] commit.py produces model commitment C
- [ ] test_model.py passes

### Stage 2: Circuit (Hour 3-7)
- [ ] compile.py runs EZKL: gen_settings -> calibrate -> compile -> setup
- [ ] prove.py generates a proof for a sample input
- [ ] verify_local.py verifies the proof with EZKL
- [ ] test_circuit.py honest flow passes
- [ ] Measure and record: proving time (s), proof size (bytes), verification time (ms)

### Stage 3: Tamper Tests (Hour 7-9)
- [ ] test_circuit.py tamper tests all pass (model_mismatch, threshold, replay)
- [ ] Document failure reasons

### Stage 4: Sidecar (Hour 9-14)
- [ ] sidecar FastAPI app runs
- [ ] /v1/prove endpoint queues jobs
- [ ] prover_worker.py proves and uploads to Lender Node (mock first, real later)
- [ ] outbox retry works
- [ ] test_sidecar.py passes

### Stage 5: Policy + Integration (Hour 14-18)
- [ ] example_policy.json signed with Ed25519
- [ ] Sidecar reads policy at startup
- [ ] Full flow: DecisionEvent -> Sidecar -> Proof -> Lender Node

### Stage 6: Docker (Hour 18-20)
- [ ] Dockerfile builds cleanly
- [ ] Works in docker-compose
- [ ] Pre-generate 5 demo proofs

## Deliverables to Dev 3 (for docker-compose)
- Container image: `sakshi-sidecar:latest`
- Exposed port: `8001` (on lsp_net only)
- Env vars: see above
- Health endpoint: `GET /healthz`
- Volume mounts: `/app/circuits/artifacts` (read-only, pre-built)

## IMPORTANT NOTES FOR AI IMPLEMENTATION

**1. EZKL is the hardest part.**
Run compile.py FIRST THING. If it fails, fall back to a mock proof generator that returns realistic-looking proof bytes for demo purposes.

**2. Proof generation is slow.**
Pre-generate proofs for 5 demo applications (approve + reject scenarios). Store them in `circuits/prebuilt_proofs/`.

**3. The mock_prover fallback.**
If EZKL times out or fails, the sidecar should have a `--mock-proofs` flag that returns pre-built proofs. This is your demo safety net.

**4. Feature order matters for EZKL witness.**
Define `FEATURE_ORDER = ['bureau_score', 'monthly_income', 'foir', ...]` as a constant in `shared/types.py`.

**5. Use integer feature_scale when doing fixed-point math.**
Multiply all floats by 1024 before ZK circuit, divide after.

**6. Keep proving async.**
Sidecar HTTP response must be instant (just returns job_id). All heavy computation happens in the background worker.
