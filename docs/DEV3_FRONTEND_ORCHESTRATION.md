# DEV 3: Frontend + Demo Orchestration - Complete Technical Specification

## Role & Ownership
Dev 3 owns the presentation layer, the client demonstration, and system integration:
1. **React Dashboard (Lender Risk & Operations View)**: Real-time UI displaying decision statistics, verified/failed status badges, proof latency metrics, tamper tests, and ledger audit verification.
2. **Mock LMS (Loan Management System)**: The RE consumer service with the fail-closed disbursal gate (`GET /v1/decisions/{id}/status`). No loan disbursal occurs unless a verifiable proof is confirmed.
3. **Master `deploy/docker-compose.yml`**: Defines the two isolated network zones (`lsp_net` and `lender_net`), bridging the sidecar, mounting shared volumes, configuring environment variables, and establishing readiness checks.
4. **Demo Orchestration & Tamper Suite**: Scripts and UI buttons to demonstrate the 5 key scenarios (Honest Flow, Model Swap Tamper, Threshold Creep Tamper, Input Alteration Tamper, and Replay Attack).

---

## Repository Structure (Branch: `feature/branch-3-frontend-demo`)

```
sakshi/
  shared/                  # READ-ONLY - frozen contracts from shared/types.py
  dashboard/
    package.json
    vite.config.ts
    tailwind.config.js
    tsconfig.json
    index.html
    Dockerfile
    nginx.conf
    src/
      main.tsx
      App.tsx
      api/
        client.ts          # Axios client communicating with Lender Node API
        types.ts           # TypeScript interfaces mirrored from shared/types.py
      components/
        StatsCards.tsx     # Summary tiles: Total, Verified, Failed, Pending, SLA Breaches
        DecisionTable.tsx  # Live paginated decisions with status badges and reason codes
        LedgerView.tsx     # Immutable audit log with cryptographic chain-valid indicator
        TamperPanel.tsx    # Interactive trigger buttons for the 5 live demo scenarios
        ProofModal.tsx     # Inspector for proof bytes, public inputs (C, X, policy_hash)
        ModelRegistry.tsx  # Models and policies currently approved by Lender
      hooks/
        useDashboard.ts    # Polling hook (5s cadence) querying /v1/dashboard/summary
      utils/
        formatters.ts      # Currency (INR), date (IST/UTC), latency formatters
        colors.ts          # Tailored status color palette (VERIFIED=emerald, FAILED=rose)
  mock_lms/
    main.py                # FastAPI mock Loan Management System
    disbursal_gate.py      # Gate client checking /v1/decisions/{id}/status
    loan_service.py        # In-memory / SQLite loan record manager
    requirements.txt
    Dockerfile
  deploy/
    docker-compose.yml     # MASTER INTEGRATION FILE
    .env.example           # Shared API keys, endpoints, and flags
    init.sh                # Startup verification & healthcheck waiter
    prometheus/
      prometheus.yml
    grafana/
      provisioning/
        datasources/sakshi.yml
      dashboards/
        sakshi_overview.json
  scripts/
    demo_seed.py           # Seeds approved model, signed policy, pre-built proofs
    run_honest_flow.py     # Executes honest flow end-to-end
    run_tamper_model.py    # Simulates silent model swap (C mismatch)
    run_tamper_threshold.py# Simulates unapproved threshold lowering
    run_tamper_input.py    # Simulates altered applicant data (X mismatch)
    run_tamper_replay.py   # Simulates replayed prior proof
    run_full_demo.py       # Orchestrates all 5 scenarios sequentially
  tests/
    test_mock_lms.py       # Gate blocking and disbursal assertions
    test_gate_integration.py # Multi-container integration verification
```

---

## Master Docker Compose Specification (`deploy/docker-compose.yml`)

The system enforces strict trust boundaries:
- `lsp_net`: Private zone. Prover sidecar runs here. Zero inbound access from the public internet.
- `lender_net`: Lender environment. Lender Node, Mock LMS, Adapter, and Dashboard run here.
- The `sidecar` container is the sole bridge: it resides in `lsp_net` and makes **outbound-only** calls to `lender-node:8000` on `lender_net`.

```yaml
version: '3.9'

networks:
  lsp_net:
    driver: bridge
  lender_net:
    driver: bridge

volumes:
  node_data:
  sidecar_data:
  circuit_artifacts:

services:
  # -------------------------------------------------------------
  # LSP ZONE (Private Model Prover)
  # -------------------------------------------------------------
  sidecar:
    image: sakshi-sidecar:latest
    build:
      context: ..
      dockerfile: sidecar/Dockerfile
    networks:
      - lsp_net
      - lender_net
    ports: []  # Isolated: No external ingress ports
    environment:
      - SAKSHI_SIDECAR_LENDER_NODE_URL=http://lender-node:8000
      - SAKSHI_SIDECAR_SIDECAR_API_KEY=${SIDECAR_API_KEY:-sakshi-dev-key}
      - SAKSHI_SIDECAR_POLICY_ID=${POLICY_ID:-pol_nbfc42_lspX_personal_v1}
      - SAKSHI_SIDECAR_NUM_WORKERS=2
    volumes:
      - circuit_artifacts:/app/circuits/artifacts:ro
      - sidecar_data:/app/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/healthz"]
      interval: 10s
      timeout: 5s
      retries: 5
    depends_on:
      lender-node:
        condition: service_healthy

  # -------------------------------------------------------------
  # LENDER ZONE (Regulated Entity Node & Disbursal Gate)
  # -------------------------------------------------------------
  lender-node:
    image: sakshi-node:latest
    build:
      context: ..
      dockerfile: node/Dockerfile
    networks:
      - lender_net
    ports:
      - "8000:8000"
    environment:
      - SAKSHI_NODE_DATABASE_URL=sqlite+aiosqlite:////app/data/sakshi.db
      - SAKSHI_NODE_SIDECAR_API_KEY=${SIDECAR_API_KEY:-sakshi-dev-key}
      - SAKSHI_NODE_LENDER_ADMIN_KEY=${LENDER_ADMIN_KEY:-lender-admin-key}
      - SAKSHI_NODE_MOCK_VERIFY=${MOCK_VERIFY:-false}
    volumes:
      - node_data:/app/data
      - circuit_artifacts:/app/circuits/artifacts:ro
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
      interval: 10s
      timeout: 5s
      retries: 10

  adapter:
    image: sakshi-adapter:latest
    build:
      context: ..
      dockerfile: adapter/Dockerfile
    networks:
      - lender_net
    ports:
      - "8003:8003"
    environment:
      - SAKSHI_ADAPTER_LENDER_NODE_URL=http://lender-node:8000
    depends_on:
      lender-node:
        condition: service_healthy

  mock-lms:
    image: sakshi-mock-lms:latest
    build:
      context: ..
      dockerfile: mock_lms/Dockerfile
    networks:
      - lender_net
      - lsp_net
    ports:
      - "8002:8002"
    environment:
      - SAKSHI_LMS_LENDER_NODE_URL=http://lender-node:8000
      - SAKSHI_LMS_SIDECAR_URL=http://sidecar:8001
    depends_on:
      lender-node:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/healthz"]
      interval: 10s
      timeout: 5s
      retries: 5

  dashboard:
    image: sakshi-dashboard:latest
    build:
      context: ../dashboard
      dockerfile: Dockerfile
    networks:
      - lender_net
    ports:
      - "3000:80"
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - lender-node
```

---

## Frontend Implementation Details

### TypeScript Data Contracts (`dashboard/src/api/types.ts`)
```typescript
export interface DecisionStatusResponse {
  decision_id: string;
  status: 'NOT_FOUND' | 'NOTICE_RECEIVED' | 'VERIFIED' | 'FAILED' | 'EXPIRED';
  model_commitment?: string;
  policy_id?: string;
  verified_at?: string;
  ledger_seq?: number;
  failure_reason?: string;
  sla_deadline?: string;
}

export interface DashboardSummary {
  total_decisions: number;
  verified: number;
  failed: number;
  pending: number;
  expired: number;
  failure_breakdown: Record<string, number>;
  recent_decisions: DecisionStatusResponse[];
  proof_latency_p50_ms?: number;
  proof_latency_p95_ms?: number;
  ledger_seq: number;
  chain_valid: boolean;
  active_models: any[];
  active_policies: any[];
}

export interface LedgerEntry {
  seq: number;
  decision_id: string;
  verification_id: string;
  status: string;
  reason?: string;
  policy_id: string;
  model_commitment: string;
  proof_hash: string;
  ts: string;
  prev_hash: string;
  row_hash: string;
}
```

### Axios Client (`dashboard/src/api/client.ts`)
```typescript
import axios from 'axios';
import { DashboardSummary, DecisionStatusResponse, LedgerEntry } from './types';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 10000,
});

export const fetchSummary = async (): Promise<DashboardSummary> => {
  const { data } = await apiClient.get<DashboardSummary>('/v1/dashboard/summary');
  return data;
};

export const fetchLedger = async (limit = 50): Promise<LedgerEntry[]> => {
  const { data } = await apiClient.get<LedgerEntry[]>(`/v1/dashboard/ledger?limit=${limit}`);
  return data;
};
```

### Interactive Tamper Panel (`dashboard/src/components/TamperPanel.tsx`)
Provides one-click live verification demonstrations:
- **Button 1: Normal Honest Flow**: Applicant meets credit criteria; proof generated and confirmed; status updates to `VERIFIED`; funds disbursed.
- **Button 2: Silent Model Swap**: Sidecar provides proof evaluated against an unauthorized model ($C_{bad}$); rejected by Lender Node with reason `MODEL_MISMATCH`. Disbursal blocked.
- **Button 3: Threshold Creep**: LSP attempts to approve borrower with claimed threshold $0.05$ instead of contractually agreed $0.20$; rejected with `THRESHOLD_MISMATCH`.
- **Button 4: Input Alteration**: Borrower income inflated at decision time; adapter compares $X'$ against independent data source; rejected with `BINDING_MISMATCH`.
- **Button 5: Replay Attack**: Resubmission of an identical historical proof; rejected with reason `REPLAY`.

---

## Mock LMS Disbursal Gate (`mock_lms/disbursal_gate.py`)

Implements the **Fail-Closed Rule**:
```python
import httpx
from fastapi import HTTPException

class DisbursalGate:
    def __init__(self, lender_node_url: str):
        self.lender_node_url = lender_node_url

    async def evaluate_and_disburse(self, decision_id: str, loan_amount: float) -> dict:
        async with httpx.AsyncClient() as client:
            try:
                res = await client.get(f"{self.lender_node_url}/v1/decisions/{decision_id}/status", timeout=5.0)
            except Exception as e:
                # Fail closed: Network error to verifier node halts disbursal
                return {
                    "disbursed": False,
                    "status": "GATE_UNREACHABLE",
                    "reason": "Fail-closed rule: Verifier node unreachable. Disbursal held."
                }

        if res.status_code == 404:
            return {"disbursed": False, "status": "NOT_FOUND", "reason": "No decision notice found."}

        data = res.json()
        status = data.get("status")

        if status == "VERIFIED":
            return {
                "disbursed": True,
                "status": "VERIFIED",
                "disbursal_reference": f"DISB-INR-{decision_id}",
                "amount": loan_amount,
                "ledger_seq": data.get("ledger_seq")
            }
        elif status == "NOTICE_RECEIVED":
            return {
                "disbursed": False,
                "status": "PENDING_PROOF",
                "reason": "Proof still being generated or verified. Disbursal on hold."
            }
        else:
            # FAILED, EXPIRED, etc.
            return {
                "disbursed": False,
                "status": status,
                "reason": f"Disbursal rejected by gate. Reason: {data.get('failure_reason')}"
            }
```

---

## Demo Seeding & Execution Script (`scripts/demo_seed.py`)

Automates initial state initialization so the team can demonstrate immediately upon container launch:
1. Calls `POST /v1/models` to register standard LR scorecard model.
2. Calls `POST /v1/models/{id}/approve` using Lender key.
3. Calls `POST /v1/policies` to register dual-signed policy `pol_nbfc42_lspX_personal_v1`.
4. Pre-seeds 3 historical decisions into the append-only ledger to show an active running hash chain.

---

## Build Checklist & Time Allocation (Dev 3)

- [ ] **Hour 0–3**: Scaffold Vite + Tailwind React app, configure `deploy/docker-compose.yml`, setup Docker network topology.
- [ ] **Hour 3–8**: Build `mock_lms` FastAPI service with fail-closed gate logic and applicant demo triggers.
- [ ] **Hour 8–14**: Complete React dashboard (`StatsCards`, `DecisionTable`, `LedgerView`, `TamperPanel`).
- [ ] **Hour 14–18**: Connect Dashboard to Lender Node API, implement polling hook, test CORS headers.
- [ ] **Hour 18–21**: Write `scripts/demo_seed.py` and integration tests (`tests/test_gate_integration.py`).
- [ ] **Hour 21–24**: Full end-to-end rehearsal with Dev 1 and Dev 2 containers; record fallback backup video.
