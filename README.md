# Sakshi (सक्षी)
### Zero-Knowledge Contract-Conformance Assurance for Digital Lending

**Sakshi** allows a bank or NBFC (Regulated Entity, RE) to cryptographically verify that a Lending Service Provider (LSP) used the contractually agreed underwriting model, decision thresholds, and compliance rules for **100% of individual credit decisions** — *without* the LSP ever disclosing its proprietary model weights, internal scoring formulas, or raw applicant feature tensors.

---

## 📚 Master Engineering Documentation Index

All core architectural, technical, and operational specifications have been generated and locked in the repository:

1. **[MASTER_PLAN.md](file:///c:/Users/Abcom/Desktop/Work/Code%20Projects/Python/Sakshi/docs/MASTER_PLAN.md)**
   - PRD Analysis & Financial Reality (RBI Digital Lending Directions 2025, FREE-AI Framework, Account Aggregator, DPDP Act)
   - Three-Zone Architecture (LSP Prover, Trust Anchor, Lender Node)
   - Cryptographic Proof Mechanism ($C$, $X$, Policy Hash, Fixed-Point Scale)
   - 24-Hour Hour-by-Hour Execution Roadmap
   - 5-Minute Live Winning Hackathon Pitch Script
   - Fallback Playbook (`MOCK_VERIFY=true` & pre-compiled proofs)

2. **[DEV1_ZKML_CORE.md](file:///c:/Users/Abcom/Desktop/Work/Code%20Projects/Python/Sakshi/docs/DEV1_ZKML_CORE.md)**
   - **Assigned Developer:** Dev 1 (ZK/ML Lead)
   - **Branch:** `feature/branch-1-zkml-core`
   - **Owned Directories:** `model/`, `circuits/`, `sidecar/`, `policy/`
   - **Scope:** Synthetic India credit dataset, LR scorecard ONNX export, EZKL Halo2 circuit compilation, Prover Sidecar with SQLite outbox, Ed25519 policy signers.

3. **[DEV2_LENDER_NODE.md](file:///c:/Users/Abcom/Desktop/Work/Code%20Projects/Python/Sakshi/docs/DEV2_LENDER_NODE.md)**
   - **Assigned Developer:** Dev 2 (Lender Node & Verifier Lead)
   - **Branch:** `feature/branch-2-lender-node`
   - **Owned Directories:** `node/`, `adapter/`
   - **Scope:** Model & Policy Registries, 9-stage Verifier Pipeline (V1 to V9), Append-only cryptographic hash chain ledger, Fail-Closed Disbursal Gate API (`GET /v1/decisions/{id}/status`), SLA monitoring, Input Binding Adapter.

4. **[DEV3_FRONTEND_ORCHESTRATION.md](file:///c:/Users/Abcom/Desktop/Work/Code%20Projects/Python/Sakshi/docs/DEV3_FRONTEND_ORCHESTRATION.md)**
   - **Assigned Developer:** Dev 3 (Frontend & DevOps Lead)
   - **Branch:** `feature/branch-3-frontend-demo`
   - **Owned Directories:** `dashboard/`, `mock_lms/`, `deploy/`, `scripts/`
   - **Scope:** React 18 + Vite + Tailwind dashboard, Mock LMS fail-closed loan consumer, Master `deploy/docker-compose.yml`, Interactive **Tamper Panel**, Automated demo seeder (`scripts/demo_seed.py`).

5. **[GIT_SETUP_AND_MERGE_GUIDE.md](file:///c:/Users/Abcom/Desktop/Work/Code%20Projects/Python/Sakshi/docs/GIT_SETUP_AND_MERGE_GUIDE.md)**
   - Git branch strategy & deterministic conflict-free single-pass merge workflow.
   - Code ownership boundary matrix.

6. **[shared/types.py](file:///c:/Users/Abcom/Desktop/Work/Code%20Projects/Python/Sakshi/shared/types.py)**
   - **Frozen Shared Contract:** Pydantic models for `DecisionEvent`, `DecisionNotice`, `ProofPayload`, `ModelRegistration`, `PolicyDocument`, `VerificationResult`, `LedgerEntry`, and cryptographic helper functions.

---

## ⚡ Quick Start Architecture Overview

```
                      [ZONE 1: LSP] (Private)
                 ┌─────────────────────────────────┐
                 │ Underwriting Model (IP Secret)  │
                 │                 │               │
                 │          Decision Event         │
                 │                 ▼               │
                 │  Prover Sidecar (Port 8001)     │
                 │  - Witness Builder              │
                 │  - EZKL Prover                  │
                 │  - SQLite Outbox                │
                 └─────────────────┬───────────────┘
                                   │ Outbound HTTPS Only
                                   │ (Notice + ZK Proof)
                                   ▼
                   [ZONE 3: RE / LENDER NODE]
 ┌───────────────────────────────────────────────────────────────────┐
 │ Lender Node (Port 8000)                                           │
 │ ├── Verifier Pipeline: V1 (Policy) -> V2 (Model C) -> V8 (EZKL)   │
 │ ├── Append-Only Audit Ledger: SHA-256 Hash Chain                  │
 │ └── Disbursal Gate API: GET /v1/decisions/{decision_id}/status    │
 └─────────────────┬───────────────────────────────▲─────────────────┘
                   │ Status: VERIFIED              │ Gate Check
                   ▼                               │
      ┌─────────────────────────┐     ┌────────────────────────────┐
      │ Mock LMS (Port 8002)    │     │ React Dashboard (Port 3000)│
      │ "No Proof, No Disbursal"│     │ - Real-Time Audit Feed     │
      │ Disburses loan to bank  │     │ - Interactive Tamper Suite │
      └─────────────────────────┘     └────────────────────────────┘
```

---

## 🚀 Running the Multi-Container System (Once Merged)

```bash
# 1. Setup environment
cp deploy/.env.example deploy/.env

# 2. Launch system with Docker Compose
docker compose -f deploy/docker-compose.yml up --build -d

# 3. Seed demo model, policy, and applicants
python scripts/demo_seed.py

# 4. Open Lender Operations & Tamper Dashboard
# URL: http://localhost:3000
```
