# SAKSHI: Master Hackathon Architecture & 24-Hour Deterministic Execution Plan

> **Product Name:** Sakshi (सक्षी - "The Witness / Verifier")  
> **Tagline:** Zero-Knowledge Contract-Conformance Assurance for Digital Lending  
> **Target Jurisdiction:** India (RBI Digital Lending Directions 2025, FREE-AI Framework, DPDP Act)  
> **Development Methodology:** 100% Deterministic AI-Agent Directed Multi-Branch Pipeline  

---

## 1. PRD Analysis, Financial Domain Reality & Strategic Scope

### 1.1 The Indian Digital Lending Dilemma (The Accountability Asymmetry)
In the Indian fintech ecosystem, modern credit disbursals operate on a severe structural tension:
- **The Regulated Entity (RE)** — the Bank or NBFC — bears 100% regulatory liability for borrower conduct, fair practices code adherence, underwriting transparency, and recovery protocols under the **Reserve Bank of India (Digital Lending) Directions, 2025** and the **FREE-AI Framework**.
- **The Lending Service Provider (LSP)** — fintech platforms such as KreditBee, Navi, MoneyTap, or Slice — owns the borrower journey (Digital Lending App, DLA), alternative-data feature engineering, and the proprietary credit scoring model.
- **The Intellectual Property Wall:** LSPs treat their model parameters, binning transformations, neural embeddings, and feature weights as trade secrets. They categorically refuse to hand raw weights over to NBFC credit committees or model escrows.
- **The Resulting Exposure:** The lender sits with open liability for underwriting decisions it has zero real-time visibility into. Lenders currently rely on sampled manual quarterly audits. Between audits, lenders are exposed to:
  1. **Silent Model Swaps:** LSP updates model version without approval to chase growth.
  2. **Threshold Creep:** LSP quietly drops underwriting score cut-offs (e.g. from $0.20$ to $0.15$) to meet monthly loan origination quotas.
  3. **Input Manipulation:** Agent or frontend tampering with self-reported salary or obligations.
  4. **Multi-RE Model Contamination:** Re-using generic underwriting across multiple balance sheets despite distinct contractual mandates.

### 1.2 The Sakshi Breakthrough
Sakshi introduces **Zero-Knowledge Machine Learning (zkML) Contract-Conformance Assurance**:
- The LSP runs an isolated **Prover Sidecar** inside its VPC.
- For every credit decision, the sidecar generates a zero-knowledge succinct proof (ZK-SNARK via EZKL/Halo2) asserting:
  $$\text{"A model with public commitment } C \text{ applied to applicant input } X \text{ produced decision } D \ge \text{threshold } T\text{"}$$
- The Lender Node verifies this proof cryptographically in **under 20 milliseconds**.
- **The Fail-Closed Rule:** The lender's Loan Management System (LMS) strictly blocks loan disbursal unless the proof passes (`no proof, no disbursal`).
- **Privacy Guarantee:** Weights, biases, salts, and unmasked raw applicant features never leave the LSP boundary.

### 1.3 24-Hour Hackathon Reality Check: MVP vs. Roadmap

| Dimension | Full PRD Vision | 24-Hour Hackathon MVP Scope | Implementation Rationale |
| :--- | :--- | :--- | :--- |
| **Model Family** | Deep NNs, CatBoost, Scorecards | **10-Feature Logistic Regression Scorecard** (+ XGBoost stretch) | LR scorecards represent >80% of regulated Indian retail underwriting. Compiles and proves deterministically within seconds. |
| **Proving Stack** | RISC Zero / SP1 / EZKL | **EZKL (Halo2) with pinned v10.4.0** | Native ONNX compilation. Predictable verification. |
| **Cryptographic Hash** | Poseidon / Poseidon2 inside circuits | **SHA-256 for commitments + EZKL internal poseidon** | Prevents ZK arithmetic circuit bloat while retaining cryptographic integrity. |
| **Database** | Distributed Postgres with append-only role | **SQLite with async aiosqlite + SQLAlchemy ORM** | Zero container setup friction, easily swapped for Postgres via ORM connection string. |
| **Network Security** | Enterprise PKI mTLS | **Docker network isolation + `X-Sakshi-Key` signed headers** | True physical separation visible across `lsp_net` and `lender_net`. |
| **Fail-safe Fallback** | N/A | **`MOCK_VERIFY=true` environment flag + Pre-computed proofs** | Guarantees an unshakeable live demo even if machine hardware throttles under EZKL compilation. |

---

## 2. System Architecture & Trust Boundaries

```
┌──────────────────────────────────────────────┐       ┌─────────────────────────────────────────────────────────┐
│              ZONE 1: LSP ENVIRONMENT         │       │                 ZONE 3: LENDER ENVIRONMENT              │
│               (Network: lsp_net)             │       │                   (Network: lender_net)                 │
│                                              │       │                                                         │
│   ┌────────────────────┐                     │       │   ┌─────────────────────┐       ┌───────────────────┐   │
│   │ Underwriting Model │                     │       │   │  Lender Node API    │       │  Mock LMS (Bank)  │   │
│   │ (Weights: SECRET)  │                     │       │   │  (Port 8000)        │       │  (Port 8002)      │   │
│   └─────────┬──────────┘                     │       │   │  - Verifier Engine  │       │  - Fail-Closed    │   │
│             │ Decision Event                 │       │   │  - Model Registry   │◄──────┤    Disbursal Gate │   │
│             ▼                                │       │   │  - Policy Engine    │       └───────────────────┘   │
│   ┌────────────────────┐                     │       │   │  - Hash Ledger      │                               │
│   │   Prover Sidecar   │                     │       │   └──────────▲──────────┘       ┌───────────────────┐   │
│   │   (Port 8001)      │                     │       │              │                  │ React Dashboard   │   │
│   │  - Witness Builder │─────────────────────┼───────┼──────────────┘                  │ (Port 3000)       │   │
│   │  - EZKL Prover     │ Outbound HTTPS Only │       │   GET /v1/decisions/{id}/status │ - Risk Monitoring │   │
│   │  - SQLite Outbox   │ (Notice + Proof)    │       │   POST /v1/proofs               │ - Tamper Demo UI  │   │
│   └────────────────────┘                     │       │                                 └───────────────────┘   │
└──────────────────────────────────────────────┘       └─────────────────────────────────────────────────────────┘
                                   │                               │
                                   ▼                               ▼
                      ┌─────────────────────────────────────────────────────────┐
                      │              ZONE 2: SHARED TRUST ANCHOR                │
                      │  - Dual-Signed Policy (Ed25519)                         │
                      │  - Model Commitment C = SHA256(weights || salt)         │
                      │  - Verification Key (VK) & Compiled Circuit Hash        │
                      └─────────────────────────────────────────────────────────┘
```

### Data Classification: What Crosses the Boundary?
1. **Never Leaves LSP:** Model weights, hyper-parameters, private salt, raw borrower features.
2. **Crosses Outbound to Lender:** Decision notice (`decision_id`, `application_id_hash`), Base64 proof, public inputs $\{C, X, \text{decision}, \text{threshold}, \text{policy\_hash}, \text{epoch}\}$.
3. **Internal Lender Only:** Loan account status, disbursal triggers, borrower identity.

---

## 3. Team Ownership & Single-Pass AI Decomposition

To achieve 100% completion by AI agents without merge conflicts, the codebase is compartmentalized into 3 branches. Each developer has 100% autonomy over their directory space.

### Branch Matrix & Deliverables

```
develop (Integration Base)
├── feature/branch-1-zkml-core        -> Dev 1: Model, Circuit, Prover Sidecar, Policy Signer
├── feature/branch-2-lender-node       -> Dev 2: Lender Node, Verifier Engine, Ledger, Adapter
└── feature/branch-3-frontend-demo    -> Dev 3: React Dashboard, Mock LMS, Docker Compose, Demo
```

#### Developer 1: ZK/ML Core Engine (`feature/branch-1-zkml-core`)
- **Assigned Directories:** `model/`, `circuits/`, `sidecar/`, `policy/`
- **Inputs:** `shared/types.py` contracts.
- **Outputs:**
  - Standardized India synthetic credit dataset generator (10,000 applicants, CIBIL range 300–900).
  - Trained Logistic Regression scorecard with ONNX export and parity report (>98% agreement).
  - EZKL circuit compile, witness builder, and proof generator producing valid Halo2 proofs.
  - Prover sidecar with transactional SQLite outbox ensuring zero dropped decisions.
  - Pre-built demo proof fixtures in `circuits/prebuilt_proofs/`.

#### Developer 2: Lender Node & Verifier Pipeline (`feature/branch-2-lender-node`)
- **Assigned Directories:** `node/`, `adapter/`
- **Inputs:** `shared/types.py` contracts, proofs uploaded from Sidecar.
- **Outputs:**
  - Model registry enforcing dual-party Ed25519 signing.
  - Verifier Engine implementing V1 through V9 verification checks (V2 Model Commitment, V4 Threshold, V6 Replay, V8 EZKL ZK Verification).
  - Append-only cryptographic hash chain ledger ($H_i = \text{SHA256}(H_{i-1} \parallel \text{row}_i)$).
  - Disbursal gate endpoint (`GET /v1/decisions/{decision_id}/status`).
  - Input Binding Adapter validating $X' \stackrel{?}{=} X$.

#### Developer 3: Frontend & Demo Orchestration (`feature/branch-3-frontend-demo`)
- **Assigned Directories:** `dashboard/`, `mock_lms/`, `deploy/`, `scripts/`
- **Inputs:** APIs exposed by Dev 1 and Dev 2.
- **Outputs:**
  - Modern React 18 + Vite + Tailwind dashboard with live 5-second polling.
  - Interactive **Tamper Panel** allowing judges to trigger honest and adversarial attacks with instant feedback.
  - Mock LMS service executing the fail-closed disbursal rule.
  - Master `deploy/docker-compose.yml` orchestrating `lsp_net` and `lender_net`.
  - Automated seeding script (`scripts/demo_seed.py`) and full demo runner (`scripts/run_full_demo.py`).

---

## 4. The 24-Hour Execution Timeline

```
Hour 00 - 02: Setup & Shared Contracts Lock
  ├── scaffold directories and initialize git branches
  └── freeze shared/types.py (Single source of truth)

Hour 02 - 08: Core Engine & Subsystem Build
  ├── Dev 1: Train LR model, export ONNX, compile EZKL circuit, generate first proof
  ├── Dev 2: Setup DB schemas, build model/policy endpoints, write V1-V7 verification
  └── Dev 3: Scaffold React Vite app, build Mock LMS fail-closed gate logic

Hour 08 - 14: Prover Sidecar, Verifier V8 & Dashboard
  ├── Dev 1: Complete Sidecar outbox and proving worker loop
  ├── Dev 2: Wire EZKL V8 zk-verification and append-only hash chain ledger
  └── Dev 3: Build dashboard components (StatsCards, DecisionTable, TamperPanel)

Hour 14 - 18: Cross-Boundary Integration
  ├── Dev 1: Test sidecar uploading real proofs to Dev 2 Lender Node
  ├── Dev 2: Validate tamper rejection codes (MODEL_MISMATCH, REPLAY, THRESHOLD)
  └── Dev 3: Connect React dashboard to Lender Node API; verify live UI polling

Hour 18 - 21: Dockerization & Orchestration
  ├── Dev 1, 2, 3: Build individual service Dockerfiles
  ├── Dev 3: Assemble master deploy/docker-compose.yml and run tests/test_gate_integration.py
  └── Dev 3: Create scripts/demo_seed.py with pre-compiled proofs

Hour 21 - 23: Deterministic Single-Pass Merge & Rehearsal
  ├── Merge branch-1, branch-2, branch-3 into release/v1.0-hackathon
  ├── Run end-to-end rehearsal using scripts/run_full_demo.py
  └── Promote release branch to main

Hour 23 - 24: Polish & Fallback Safety Net
  ├── Record screen demo video as backup
  ├── Validate benchmark metrics table for presentation
  └── Final code freeze
```

---

## 5. Verification Pipeline (V1 to V9 Specification)

The Lender Node executes a 9-step verification pipeline ordered from computationally cheapest to most expensive:

1. **V1_POLICY_EXISTS:** Confirms `policy_id` exists in database and current timestamp is within `valid_from` and `valid_to`.
2. **V2_MODEL_APPROVED:** Extracts model commitment $C$ from public inputs and confirms it matches an active `APPROVED` model. *(Catches silent model swaps)*.
3. **V3_POLICY_HASH_MATCH:** Compares `public_inputs.policy_hash` against stored policy SHA-256 hash.
4. **V4_THRESHOLD_MATCH:** Compares `public_inputs.threshold` against contractually signed threshold in policy. *(Catches unapproved threshold creep)*.
5. **V5_WINDOW_VALID:** Validates `public_inputs.epoch` matches current or preceding calendar date ($YYYYMMDD$).
6. **V6_UNIQUENESS:** Verifies `SHA256(proof_bytes)` has not been recorded previously in `proof_records`. *(Catches replay attacks)*.
7. **V7_DECISION_MATCH:** Confirms decision integer in public inputs ($1$ or $0$) matches the initial decision notice.
8. **V8_ZK_VERIFY:** Invokes `ezkl.verify(proof, vk, settings)` using registered verification key.
9. **V9_HARD_RULES:** Validates that hard policy constraints (e.g. minimum bureau score or maximum FOIR) were not breached.

---

## 6. Live Demo Script (5-Minute Winning Pitch)

| Scene | Action | Visual Display / Outcome | Key Message |
| :--- | :--- | :--- | :--- |
| **1. The Blind Spot (45s)** | Present standard lender LMS with basic "Approve/Reject" flag. | Show that lender has zero insight into whether agreed model was run. | "Lenders carry 100% regulatory liability for underwriting they cannot see." |
| **2. Cryptographic Onboarding (45s)** | Execute `demo_seed.py` registering model and dual-signed policy. | Terminal shows only $\{C, \text{circuit\_hash}, \text{VK}\}$ crossing network. | "Weights never leave the LSP. Zero IP exposure." |
| **3. The Honest Disbursal (60s)** | Click **[Run Honest Flow]** on Tamper Panel. | Sidecar proves (2s); Lender verifies (12ms); Dashboard lights up green `VERIFIED`; LMS disburses funds. | "Proving happens asynchronously off the UX path. Disbursal occurs safely." |
| **4. Tamper Test 1: Model Swap (45s)** | Click **[Tamper: Model Swap]**. | Status updates to red `FAILED` with code `MODEL_MISMATCH`. Disbursal blocked. | "LSP cannot quietly deploy an unapproved model." |
| **5. Tamper Test 2: Threshold Creep (45s)** | Click **[Tamper: Threshold Change]**. | Verification fails with `THRESHOLD_MISMATCH`. Disbursal blocked. | "LSP cannot lower cut-offs to inflate loan volumes." |
| **6. Tamper Test 3: Replay Attack (45s)** | Click **[Tamper: Replay Attack]**. | Verification fails with `REPLAY`. Disbursal blocked. | "Historical proofs cannot be re-used for new applicants." |
| **7. Immutable Audit & Numbers (45s)** | Open `/ledger` tab; show valid hash chain and benchmark table. | Chain Valid: TRUE. Cost: <₹0.01 per decision. Proof size: ~40KB. | "Mathematical assurance ready for RBI audit inspections." |

---

## 7. Emergency Fallback Playbook

1. **Slow CPU Proving during Demo:** Dev 1 provides pre-generated proofs in `circuits/prebuilt_proofs/`. The sidecar serves pre-built proofs instantly when running with `--mock-proofs`.
2. **EZKL Verification Library Bottleneck:** The Lender Node supports `SAKSHI_NODE_MOCK_VERIFY=true`. In this mode, V1–V7 and V9 tamper checks remain 100% active and functional, while V8 cryptographic verification returns passing.
3. **Network or Container Glitch:** A self-contained SQLite and mock server script can run directly in a single terminal with zero docker dependencies.
