# DEV 2: Lender Node — Complete Technical Specification

> [!IMPORTANT]
> **Branch:** `feature/branch-2-lender-node`
> **Owns:** `node/`, `adapter/`, `deploy/node/`, `tests/test_*` (node-side)
> **Reads (never modifies):** `shared/` — shared types and contracts

---

## 1. Role & System Position

Dev 2 builds the **heart of the Sakshi system**: the Lender Node. This is a FastAPI service that:

1. Receives model registrations from the LSP Sidecar and lets the lender approve/reject them
2. Receives dual-signed policy documents and validates both signatures
3. Receives decision notices — starts the SLA clock the moment one arrives
4. Receives ZK proofs and runs a 9-step cryptographic verification pipeline
5. Maintains a **hash-chained, insert-only audit ledger**
6. Exposes a **disbursal gate API** — the Mock LMS calls this before releasing funds
7. Serves aggregated data to the Dashboard API (polled by Dev 3 React frontend)

---

## 2. Repository Structure

```
sakshi/
  shared/                    # READ-ONLY — shared contracts/types (from Dev 1)
  node/
    main.py                  # FastAPI app entrypoint, lifespan hooks
    config.py                # Pydantic Settings from env vars
    models.py                # SQLAlchemy ORM models (all tables)
    database.py              # DB engine, session factory, create_all()
    routes/
      models_route.py        # /v1/models  — registration + approval
      policies_route.py      # /v1/policies
      decisions_route.py     # /v1/decisions — start SLA clock
      proofs_route.py        # /v1/proofs — receive + async verify
      gate_route.py          # /v1/decisions/{id}/status — DISBURSAL GATE
      ledger_route.py        # /v1/ledger/export
      bindings_route.py      # /v1/input-bindings
      dashboard_route.py     # /v1/dashboard/* — frontend data
      webhooks_route.py      # outbound webhook delivery
    services/
      verifier.py            # ZK proof verification pipeline (V1-V9)
      policy_engine.py       # policy loading and hash validation
      ledger.py              # hash-chain logic + append-only writes
      sla_monitor.py         # asyncio background SLA timer
      webhook_service.py     # outbound HMAC-signed webhook + retry
    requirements.txt
    Dockerfile
  adapter/
    main.py                  # Input Binding Adapter — separate FastAPI :8003
    binder.py                # recompute X prime from lender-side data, compare to X
    requirements.txt
    Dockerfile
  tests/
    conftest.py
    test_models_route.py
    test_policies_route.py
    test_decisions_route.py
    test_proofs_route.py
    test_gate_route.py
    test_ledger.py
    test_verifier.py
    test_sla_monitor.py
  deploy/
    node/
      docker-compose.yml
```

---

## 3. Database Schema

Use **SQLAlchemy 2.x async** with `aiosqlite` for the hackathon. All model definitions in `node/models.py`.

### 3.1 RegisteredModel

```python
class RegisteredModel(Base):
    __tablename__ = 'registered_models'
    id                  = Column(String, primary_key=True)
    commitment          = Column(String, nullable=False)       # SHA-256 hex = C
    circuit_hash        = Column(String, nullable=False)
    vk                  = Column(Text, nullable=False)         # base64 EZKL VK
    feature_schema_hash = Column(String)
    parity_report       = Column(JSON)
    lsp_sig             = Column(String)
    lsp_pubkey          = Column(String)
    status              = Column(String, default='PENDING_APPROVAL')
    # PENDING_APPROVAL | APPROVED | REJECTED | REVOKED
    lender_sig          = Column(String)
    registered_at       = Column(DateTime, default=datetime.utcnow)
    approved_at         = Column(DateTime)
    revoked_at          = Column(DateTime)
    grace_until         = Column(DateTime)
```

### 3.2 Policy

```python
class Policy(Base):
    __tablename__ = 'policies'
    policy_id            = Column(String, primary_key=True)
    version              = Column(Integer)
    lender_id            = Column(String)
    lsp_id               = Column(String)
    product              = Column(String)
    model_commitment     = Column(String)
    circuit_hash         = Column(String)
    feature_schema_hash  = Column(String)
    decision_threshold   = Column(Float)
    fixed_point_scale    = Column(Integer)
    hard_rules           = Column(JSON)
    proof_sla_minutes    = Column(Integer)
    valid_from           = Column(DateTime)
    valid_to             = Column(DateTime)
    lsp_sig              = Column(String)
    lender_sig           = Column(String)
    lsp_pubkey           = Column(String)
    lender_pubkey        = Column(String)
    policy_hash          = Column(String)   # SHA-256 of canonical policy JSON
    created_at           = Column(DateTime)
    status               = Column(String, default='ACTIVE')
    # ACTIVE | EXPIRED | REVOKED
```

### 3.3 Decision

```python
class Decision(Base):
    __tablename__ = 'decisions'
    decision_id         = Column(String, primary_key=True)
    application_id_hash = Column(String)
    policy_id           = Column(String, ForeignKey('policies.policy_id'))
    decision            = Column(Integer)   # 1=approve, 0=reject
    ts                  = Column(DateTime)
    status              = Column(String, default='NOTICE_RECEIVED')
    # NOT_FOUND -> NOTICE_RECEIVED -> VERIFIED | FAILED | EXPIRED
    sla_deadline        = Column(DateTime)  # ts + policy.proof_sla_minutes
    received_at         = Column(DateTime, default=datetime.utcnow)
    verified_at         = Column(DateTime)
    verification_id     = Column(String)
    model_commitment    = Column(String)
    ledger_seq          = Column(Integer)
    failure_reason      = Column(String)
    # MODEL_MISMATCH | THRESHOLD_MISMATCH | INVALID_PROOF | REPLAY | EXPIRED | POLICY_INVALID
```

### 3.4 ProofRecord

```python
class ProofRecord(Base):
    __tablename__ = 'proof_records'
    id            = Column(String, primary_key=True)   # = verification_id
    decision_id   = Column(String, ForeignKey('decisions.decision_id'))
    proof_hash    = Column(String, unique=True)        # SHA-256 of proof bytes — REPLAY GUARD
    proof_blob    = Column(LargeBinary)
    public_inputs = Column(JSON)                       # {policy_hash, C, X, decision, threshold, epoch}
    status        = Column(String, default='PENDING')  # PENDING | VERIFIED | FAILED
    reason        = Column(String)
    submitted_at  = Column(DateTime, default=datetime.utcnow)
```

### 3.5 LedgerEntry — APPEND-ONLY

```python
class LedgerEntry(Base):
    __tablename__ = 'ledger'
    seq              = Column(Integer, primary_key=True, autoincrement=True)
    decision_id      = Column(String)
    verification_id  = Column(String)
    status           = Column(String)    # VERIFIED | FAILED | EXPIRED
    reason           = Column(String)
    policy_id        = Column(String)
    model_commitment = Column(String)
    proof_hash       = Column(String)
    ts               = Column(DateTime)
    prev_hash        = Column(String)    # row_hash of the previous row
    row_hash         = Column(String)    # SHA-256(prev_hash || canonical_json(row_without_row_hash))
    # CRITICAL: NO UPDATE or DELETE — EVER. LedgerService.append() is the only write path.
```

### 3.6 InputBinding

```python
class InputBinding(Base):
    __tablename__ = 'input_bindings'
    id                  = Column(String, primary_key=True)
    application_id_hash = Column(String)
    x_prime             = Column(String)   # recomputed from lender-side features
    decision_id         = Column(String)
    bound_at            = Column(DateTime, default=datetime.utcnow)
    binding_status      = Column(String)   # MATCHED | MISMATCH
```

### 3.7 IdempotencyKey

```python
class IdempotencyKey(Base):
    __tablename__ = 'idempotency_keys'
    key        = Column(String, primary_key=True)   # Idempotency-Key header value
    response   = Column(JSON)                        # cached 202 body
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

## 4. API Specification

**Base URL:** `http://lender-node:8000`  
**Sidecar auth:** `X-Sakshi-Key: {SAKSHI_NODE_SIDECAR_API_KEY}`  
**Lender admin auth:** `X-Lender-Key: {SAKSHI_NODE_LENDER_ADMIN_KEY}`

### 4.1 Model Registration

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/v1/models` | POST | X-Sakshi-Key | Register model, validate lsp_sig → 201 PENDING_APPROVAL |
| `/v1/models/{id}/approve` | POST | X-Lender-Key | Approve model, validate lender_sig → 200 APPROVED |
| `/v1/models/{id}` | GET | — | Get model (VK blob omitted) |
| `/v1/models` | GET | — | List all models with status |

**Errors:** `400 INVALID_SIGNATURE`, `409 ALREADY_REGISTERED`, `404 NOT_FOUND`

### 4.2 Policies

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/policies` | POST | Validate BOTH lsp_sig AND lender_sig. Model must be APPROVED. → 201 |
| `/v1/policies/{id}` | GET | Return full PolicyDocument |

**Errors:** `400 INVALID_SIGNATURE`, `400 MODEL_NOT_APPROVED`, `409 ALREADY_EXISTS`

### 4.3 Decisions (from Sidecar)

**POST /v1/decisions**
- Auth: X-Sakshi-Key
- Creates Decision with `status=NOTICE_RECEIVED`
- Sets `sla_deadline = ts + policy.proof_sla_minutes`
- Returns: `202`
- Errors: `400 POLICY_NOT_FOUND`, `409 ALREADY_EXISTS`

**GET /v1/decisions/{id}/status — THE GATE API**
```json
{
  "decision_id": "...",
  "status": "VERIFIED | FAILED | EXPIRED | NOTICE_RECEIVED",
  "model_commitment": "...",
  "policy_id": "...",
  "verified_at": "...",
  "ledger_seq": 42,
  "failure_reason": null
}
```
> The Mock LMS calls this before releasing funds. If status != "VERIFIED", no disbursal.

### 4.4 Proofs (from Sidecar)

**POST /v1/proofs**
- Auth: X-Sakshi-Key
- Required header: `Idempotency-Key: <uuid>`
- Enqueues verification via BackgroundTasks
- Returns: `202 { verification_id, status: "PENDING" }`
- On duplicate Idempotency-Key: return cached 202 immediately

### 4.5 Supporting Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/input-bindings` | POST | Compare x_prime to X in proof public inputs, store MATCHED/MISMATCH |
| `/v1/ledger/export?from=&to=` | GET | Full chain export with `chain_valid: bool` |
| `/v1/dashboard/summary` | GET | Aggregated stats (polled every 5s by Dev 3 frontend) |
| `/v1/dashboard/decisions?limit=&offset=&status=` | GET | Paginated decisions |
| `/v1/dashboard/ledger?limit=` | GET | Recent ledger entries |
| `/healthz` | GET | `{ status: "ok", ledger_seq: int, db: "ok" }` |
| `/metrics` | GET | Prometheus format metrics |
| `/docs` | GET | FastAPI auto-generated Swagger UI |

**Prometheus Metrics:**
```
sakshi_decisions_total{status="VERIFIED|FAILED|EXPIRED|NOTICE_RECEIVED"}
sakshi_verification_duration_seconds (histogram)
sakshi_sla_breaches_total
sakshi_ledger_seq
```

---

## 5. Verification Pipeline (services/verifier.py)

Runs synchronously in a BackgroundTask. Target: < 100 ms. Steps ordered cheap-to-expensive.

| Step | Name | Check | Failure Reason |
|------|------|--------|----------------|
| V1 | POLICY_EXISTS | policy_id known and status = ACTIVE | POLICY_INVALID |
| V2 | MODEL_APPROVED | public_inputs.C matches APPROVED RegisteredModel | MODEL_MISMATCH |
| V3 | POLICY_HASH_MATCH | public_inputs.policy_hash == stored policy.policy_hash | POLICY_HASH_MISMATCH |
| V4 | THRESHOLD_MATCH | public_inputs.threshold == policy.decision_threshold | THRESHOLD_MISMATCH |
| V5 | WINDOW_VALID | public_inputs.epoch matches today or yesterday | STALE_EPOCH |
| V6 | UNIQUENESS | proof_hash NOT in proof_records | REPLAY |
| V7 | DECISION_MATCH | public_inputs.decision == DecisionNotice.decision | DECISION_MISMATCH |
| V8 | ZK_VERIFY | ezkl.verify(proof, public_inputs, vk) == True | INVALID_PROOF |
| V9 | HARD_RULES | All policy.hard_rules satisfied | HARD_RULE_VIOLATION |

```python
VERIFICATION_STEPS = [
    'V1_POLICY_EXISTS', 'V2_MODEL_APPROVED', 'V3_POLICY_HASH_MATCH',
    'V4_THRESHOLD_MATCH', 'V5_WINDOW_VALID', 'V6_UNIQUENESS',
    'V7_DECISION_MATCH', 'V8_ZK_VERIFY', 'V9_HARD_RULES',
]

class VerificationPipeline:
    def run(self, proof_payload, policy, model) -> VerificationResult:
        for step in VERIFICATION_STEPS:
            result = self._run_step(step, proof_payload, policy, model)
            if not result.passed:
                return VerificationResult(status='FAILED', reason=result.reason, step=step)
        return VerificationResult(status='VERIFIED')
```

### V8 — EZKL ZK Verification

```python
import ezkl, base64, tempfile, os

def zk_verify(proof_b64: str, public_inputs: dict, vk_b64: str, settings_path: str) -> bool:
    proof_bytes = base64.b64decode(proof_b64)
    vk_bytes    = base64.b64decode(vk_b64)
    with tempfile.NamedTemporaryFile(suffix='.proof', delete=False) as pf:
        pf.write(proof_bytes); proof_path = pf.name
    with tempfile.NamedTemporaryFile(suffix='.vk', delete=False) as vf:
        vf.write(vk_bytes); vk_path = vf.name
    try:
        return ezkl.verify(proof_path, settings_path, vk_path)
    finally:
        os.unlink(proof_path); os.unlink(vk_path)
```

> settings.json must be bit-for-bit identical to what Dev 1 used in ezkl.prove(). Dev 3 mounts this as a shared Docker volume at SAKSHI_NODE_EZKL_SETTINGS_PATH.

### V9 — Hard Rules

```python
def check_hard_rules(rules: list[dict], public_inputs: dict) -> StepResult:
    ops = {'eq': lambda v,t: v==t, 'gte': lambda v,t: v>=t, 'lte': lambda v,t: v<=t,
           'gt': lambda v,t: v>t, 'lt': lambda v,t: v<t}
    for rule in rules:
        if not ops[rule['op']](public_inputs.get(rule['field']), rule['value']):
            return StepResult(passed=False, reason='HARD_RULE_VIOLATION')
    return StepResult(passed=True)
```

---

## 6. Audit Ledger (services/ledger.py)

> CRITICAL: Never issue UPDATE or DELETE on ledger. LedgerService.append() is the ONLY write path.

```python
class LedgerService:
    def append(self, session, decision_id, verification_id, status,
               reason, policy_id, model_commitment, proof_hash) -> LedgerEntry:
        # 1. Get prev_hash
        last = session.query(LedgerEntry).order_by(LedgerEntry.seq.desc()).first()
        prev_hash = last.row_hash if last else 'GENESIS'
        # 2. Build canonical row (no row_hash field)
        row_data = {
            'decision_id': decision_id, 'verification_id': verification_id,
            'status': status, 'reason': reason, 'policy_id': policy_id,
            'model_commitment': model_commitment, 'proof_hash': proof_hash,
            'ts': datetime.utcnow().isoformat()
        }
        canonical = json.dumps(row_data, sort_keys=True, separators=(',', ':'))
        # 3. Compute row_hash = SHA-256(prev_hash || canonical)
        row_hash = hashlib.sha256((prev_hash + canonical).encode()).hexdigest()
        # 4. Insert — the ONLY write path
        entry = LedgerEntry(**row_data, prev_hash=prev_hash, row_hash=row_hash)
        session.add(entry)
        session.commit()
        return entry

    def verify_chain(self, session) -> tuple[bool, Optional[int]]:
        """Walk all rows, recompute row_hash, return (is_valid, broken_at_seq)."""
        prev_hash = 'GENESIS'
        for row in session.query(LedgerEntry).order_by(LedgerEntry.seq).all():
            row_data = {k: getattr(row, k) for k in
                        ['decision_id','verification_id','status','reason',
                         'policy_id','model_commitment','proof_hash']}
            row_data['ts'] = row.ts.isoformat()
            canonical = json.dumps(row_data, sort_keys=True, separators=(',', ':'))
            expected  = hashlib.sha256((prev_hash + canonical).encode()).hexdigest()
            if expected != row.row_hash:
                return False, row.seq
            prev_hash = row.row_hash
        return True, None
```

---

## 7. SLA Monitor (services/sla_monitor.py)

```python
async def sla_monitor_loop(db_session_factory, ledger_service, webhook_service):
    """Background asyncio task — poll every 30 seconds."""
    while True:
        await asyncio.sleep(30)
        async with db_session_factory() as session:
            now = datetime.utcnow()
            expired = session.query(Decision).filter(
                Decision.status == 'NOTICE_RECEIVED',
                Decision.sla_deadline < now
            ).all()
            for d in expired:
                d.status = 'EXPIRED'
                d.failure_reason = 'EXPIRED'
                ledger_service.append(session, d.decision_id, None, 'EXPIRED',
                                      'EXPIRED', d.policy_id, d.model_commitment or '', None)
                await webhook_service.send(d, event='SLA_BREACH')
            session.commit()

# Register in main.py lifespan:
@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(sla_monitor_loop(...))
    yield
    task.cancel()
```

---

## 8. Webhook Service (services/webhook_service.py)

```python
class WebhookService:
    async def send(self, decision: Decision, event: str, retries: int = 3):
        payload = {'event': event, 'decision_id': decision.decision_id,
                   'status': decision.status, 'ts': datetime.utcnow().isoformat()}
        body    = json.dumps(payload, sort_keys=True)
        sig     = hmac.new(self.secret.encode(), body.encode(), hashlib.sha256).hexdigest()
        headers = {'Content-Type': 'application/json', 'X-Sakshi-Signature': sig}
        for attempt in range(retries):
            try:
                r = await self.client.post(self.url, content=body, headers=headers, timeout=5)
                if r.status_code < 500:
                    return
            except httpx.RequestError:
                pass
            await asyncio.sleep(2 ** attempt)   # exponential backoff: 1s, 2s, 4s
```

---

## 9. Input Binding Adapter (adapter/)

Separate FastAPI service on :8003. Lenders recompute X' from their own AA/bureau data and compare to X from the ZK proof.

```python
# adapter/binder.py
async def bind(application_id_hash: str, features: dict, lender_node_url: str) -> dict:
    canonical = json.dumps(features, sort_keys=True, separators=(',', ':'))
    x_prime   = hashlib.sha256(canonical.encode()).hexdigest()
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{lender_node_url}/v1/input-bindings",
            json={"application_id_hash": application_id_hash, "x_prime": x_prime}
        )
    return r.json()   # { binding_status: 'MATCHED' | 'MISMATCH' }

# Adapter API:
# POST /v1/bind
# Request:  { application_id_hash: str, features: dict }
# Response: { bound: bool, binding_status: 'MATCHED' | 'MISMATCH' }
```

---

## 10. Test Suite

### test_verifier.py — CRITICAL

```python
def test_honest_flow_verifies():
    """Valid proof, all V1-V9 pass -> VERIFIED"""

def test_model_mismatch_fails_v2():
    """Mutate C in public_inputs -> FAILED: MODEL_MISMATCH"""

def test_policy_hash_mismatch_fails_v3():
    """Mutate policy_hash in public_inputs -> FAILED: POLICY_HASH_MISMATCH"""

def test_threshold_mismatch_fails_v4():
    """Proof claims threshold=0.05, policy says 0.20 -> FAILED: THRESHOLD_MISMATCH"""

def test_replay_detected_v6():
    """Submit identical proof twice -> second: FAILED: REPLAY"""

def test_invalid_proof_bytes_fails_v8():
    """Random bytes as proof -> FAILED: INVALID_PROOF"""

def test_expired_sla_sets_status():
    """Decision with past sla_deadline, run monitor -> status == EXPIRED"""
```

### test_ledger.py

```python
def test_chain_integrity_valid():
    """Append 5 entries -> verify_chain() returns (True, None)"""

def test_chain_tamper_detected():
    """Append 5, raw-SQL mutate row 3 -> verify_chain() returns (False, 3)"""

def test_ledger_insert_only():
    """No update/delete methods on LedgerService; ORM UPDATE blocked at service layer"""

def test_genesis_is_first_prev_hash():
    """First entry has prev_hash == 'GENESIS'"""
```

### test_gate_route.py

```python
def test_gate_returns_verified_for_valid_proof():
    """register -> approve -> policy -> notice -> valid proof -> GET status -> VERIFIED"""

def test_gate_returns_failed_for_invalid_proof():
    """Tampered proof -> GET status -> FAILED"""

def test_gate_returns_pending_before_proof():
    """Notice only, no proof -> GET status -> NOTICE_RECEIVED"""

def test_gate_returns_expired_after_sla():
    """Past timestamp notice, run SLA monitor -> GET status -> EXPIRED"""
```

---

## 11. Docker

### node/Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "node.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### node/requirements.txt

```
ezkl==10.4.0
fastapi==0.111.0
uvicorn[standard]==0.30.1
sqlalchemy==2.0.30
aiosqlite==0.20.0
httpx==0.27.0
cryptography==42.0.8
pydantic==2.7.1
pydantic-settings==2.3.0
prometheus-client==0.20.0
```

---

## 12. Environment Variables

```env
SAKSHI_NODE_DATABASE_URL=sqlite+aiosqlite:///./data/sakshi.db
SAKSHI_NODE_SIDECAR_API_KEY=dev-shared-secret-change-in-prod
SAKSHI_NODE_LENDER_ADMIN_KEY=lender-admin-secret
SAKSHI_NODE_LENDER_PUBKEY=<hex Ed25519 pubkey>
SAKSHI_NODE_LSP_PUBKEY=<hex Ed25519 pubkey>
SAKSHI_NODE_WEBHOOK_SECRET=webhook-hmac-secret
SAKSHI_NODE_MOCK_LMS_WEBHOOK_URL=http://mock-lms:8002/webhooks/sakshi
SAKSHI_NODE_EZKL_SETTINGS_PATH=/app/shared/settings.json
SAKSHI_NODE_MOCK_VERIFY=false
```

---

## 13. Port Assignments

| Service | Port | Networks |
|---------|------|----------|
| node | 8000 | lsp_net (inbound sidecar) + lender_net (LMS + dashboard) |
| adapter | 8003 | lender_net only |

---

## 14. Build Stages & Checklist

### Stage 1 — Database & Models (Hour 0-2)
- [ ] models.py: All 6+1 ORM tables defined
- [ ] database.py: Async engine, session factory, create_all() on startup
- [ ] Basic CRUD confirmed in scratch test

### Stage 2 — Model Registration & Policies (Hour 2-6)
- [ ] POST /v1/models validates lsp_sig, creates PENDING_APPROVAL
- [ ] POST /v1/models/{id}/approve validates lender_sig, sets APPROVED
- [ ] POST /v1/policies validates both sigs, checks model is APPROVED
- [ ] test_models_route.py all green
- [ ] test_policies_route.py all green

### Stage 3 — Decision Notice & Proof Pipeline (Hour 6-12)
- [ ] POST /v1/decisions creates decision, sets SLA deadline
- [ ] POST /v1/proofs idempotency check, BackgroundTasks verification
- [ ] V1-V7 verification steps implemented and unit-tested
- [ ] V8 with MOCK_VERIFY=true passing
- [ ] V8 real EZKL passing with Dev 1 proof
- [ ] V9 hard rules passing
- [ ] Ledger appended after every verification result
- [ ] test_verifier.py ALL tamper tests pass
- [ ] test_decisions_route.py all green
- [ ] test_proofs_route.py all green

### Stage 4 — Gate API & Ledger (Hour 12-16)
- [ ] GET /v1/decisions/{id}/status returns correct status + ledger_seq
- [ ] GET /v1/ledger/export returns chain_valid: true
- [ ] verify_chain() detects raw-SQL tamper
- [ ] SLA monitor marks expired decisions, writes ledger
- [ ] test_ledger.py all green
- [ ] test_gate_route.py all green

### Stage 5 — Dashboard & Adapter (Hour 16-19)
- [ ] /v1/dashboard/summary returns correct aggregates (SQL GROUP BY, not Python loops)
- [ ] /v1/dashboard/decisions pagination works
- [ ] Adapter POST /v1/bind recomputes X', compares, stores
- [ ] Webhook fires on FAILED and SLA_BREACH events

### Stage 6 — Docker (Hour 19-22)
- [ ] node/Dockerfile builds cleanly
- [ ] adapter/Dockerfile builds cleanly
- [ ] End-to-end in docker-compose with SQLite volume
- [ ] GET /healthz returns 200 in container
- [ ] GET /docs returns Swagger UI

---

## 15. Deliverables to Dev 3

| Item | Value |
|------|-------|
| Node image | sakshi-node:latest |
| Adapter image | sakshi-adapter:latest |
| Node port | 8000 (lsp_net + lender_net) |
| Adapter port | 8003 (lender_net only) |
| Health endpoint | GET /healthz |
| Swagger docs | GET /docs |
| SQLite volume | /app/data/sakshi.db |
| EZKL settings volume | /app/shared/settings.json (shared with Dev 1) |

---

## 16. Key Implementation Notes

1. **SAKSHI_NODE_MOCK_VERIFY=true** — Skip V8 during early dev. Flip to false once Dev 1 generates real proofs.

2. **settings.json dependency** — Must be bit-for-bit identical to what Dev 1 used in ezkl.prove(). If V8 fails mysteriously, this is the first thing to check.

3. **Ledger immutability** — LedgerService.append() is the single write path. No update_ledger() or delete_ledger() methods. Every verification outcome (VERIFIED, FAILED, EXPIRED) gets a ledger entry.

4. **Async proof verification** — POST /v1/proofs uses FastAPI BackgroundTasks so the sidecar gets immediate 202. Verification runs in the background.

5. **Dashboard polling** — Dev 3 polls /v1/dashboard/summary every 5 seconds. Use SQL GROUP BY for aggregates, not Python loops over all rows.

6. **Ed25519 signatures** — Use `cryptography` library (Ed25519PublicKey.verify()). Canonical JSON: sort_keys=True, separators=(',', ':') — same as Dev 1.

7. **Replay detection (V6)** — proof_hash = SHA-256(proof_bytes) stored with UNIQUE constraint. Duplicate proof for any decision_id must fail.

8. **State machine** — Advance Decision only NOTICE_RECEIVED -> VERIFIED|FAILED|EXPIRED. Never go backward. SLA monitor and proof verifier are the only writers.
