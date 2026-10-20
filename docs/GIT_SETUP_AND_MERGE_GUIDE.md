# SAKSHI - Git Setup & Single-Pass Merge Guide

## 1. Branch Strategy & Domain Isolation

To achieve a deterministic, 100% AI-generated codebase in 24 hours without git conflicts, each developer strictly works within an isolated functional domain and an assigned git branch.

```
                  [main] (Production / Submission)
                     ▲
                     │ (Single-pass merge in Hour 22-23)
                     │
                 [develop] (Integration Base)
               ▲     ▲     ▲
               │     │     │
  ┌────────────┴┐    │     └────────────┐
  │                  │                  │
[branch-1]      [branch-2]          [branch-3]
(ZK/ML Core)    (Lender Node)      (Frontend/Orch)
Dev 1           Dev 2              Dev 3
```

---

## 2. Directory Ownership Matrix

| Directory | Owner Branch | Developer | Purpose | Modification Rules |
| :--- | :--- | :--- | :--- | :--- |
| `shared/` | `develop` | **All** | Pydantic contracts & constants | **FROZEN at Hour 2**. Zero edits without consensus. |
| `model/` | `feature/branch-1-zkml-core` | Dev 1 | Synthetic data, training, ONNX export | Dev 1 exclusive |
| `circuits/` | `feature/branch-1-zkml-core` | Dev 1 | EZKL compilation, witness, proof generation | Dev 1 exclusive |
| `sidecar/` | `feature/branch-1-zkml-core` | Dev 1 | Prover worker, outbox, outbound client | Dev 1 exclusive |
| `policy/` | `feature/branch-1-zkml-core` | Dev 1 | Policy schemas, signing utilities | Dev 1 exclusive |
| `node/` | `feature/branch-2-lender-node` | Dev 2 | Lender Node API, verifier pipeline, ledger | Dev 2 exclusive |
| `adapter/` | `feature/branch-2-lender-node` | Dev 2 | Input binding adapter ($X' \stackrel{?}{=} X$) | Dev 2 exclusive |
| `dashboard/` | `feature/branch-3-frontend-demo` | Dev 3 | Vite + React + Tailwind operations UI | Dev 3 exclusive |
| `mock_lms/` | `feature/branch-3-frontend-demo` | Dev 3 | Fail-closed disbursal gate client | Dev 3 exclusive |
| `deploy/` | `feature/branch-3-frontend-demo` | Dev 3 | `docker-compose.yml`, Prometheus, Grafana | Dev 3 exclusive |
| `scripts/` | `feature/branch-3-frontend-demo` | Dev 3 | Demo seeder, tamper test runners | Dev 3 exclusive |
| `tests/` | Dedicated to subdirs | Respective | Isolated per-branch tests | Respective owners |

---

## 3. Initial Setup Commands (Hour 0)

Execute these commands once to initialize the branches:

```bash
# 1. Switch to clean base branch
git checkout -b develop
git push -u origin develop

# 2. Commit shared contracts (Frozen after Hour 2)
git add shared/
git commit -m "chore(shared): freeze core pydantic contracts and types"
git push origin develop

# 3. Create Dev 1 Branch
git checkout -b feature/branch-1-zkml-core develop
git push -u origin feature/branch-1-zkml-core

# 4. Create Dev 2 Branch
git checkout develop
git checkout -b feature/branch-2-lender-node develop
git push -u origin feature/branch-2-lender-node

# 5. Create Dev 3 Branch
git checkout develop
git checkout -b feature/branch-3-frontend-demo develop
git push -u origin feature/branch-3-frontend-demo
```

---

## 4. Single-Pass Merge Procedure (Hour 22)

Because concerns and directories are 100% disjoint, git merges are deterministic fast-forwards with zero merge conflicts.

```bash
# Step 1: Ensure local working trees are clean and pushed
git fetch --all

# Step 2: Checkout an integration candidate branch
git checkout develop
git pull origin develop
git checkout -b release/v1.0-hackathon

# Step 3: Merge Branch 1 (ZK/ML Core)
git merge --no-ff origin/feature/branch-1-zkml-core -m "merge: ZK/ML Core pipeline (Branch 1)"

# Step 4: Merge Branch 2 (Lender Node)
git merge --no-ff origin/feature/branch-2-lender-node -m "merge: Lender Node & Verifier Engine (Branch 2)"

# Step 5: Merge Branch 3 (Frontend & Orchestration)
git merge --no-ff origin/feature/branch-3-frontend-demo -m "merge: Dashboard & Docker Orchestration (Branch 3)"

# Step 6: Verify Single-Pass Build
docker compose -f deploy/docker-compose.yml build
docker compose -f deploy/docker-compose.yml up -d

# Step 7: Run Integration Smoke Test
python scripts/demo_seed.py
python -m pytest tests/test_gate_integration.py

# Step 8: Promote to Main
git checkout main
git merge --no-ff release/v1.0-hackathon -m "release: Sakshi v1.0.0 complete hackathon build"
git tag -a v1.0.0-hackathon -m "Sakshi 24h Hackathon Final Release"
git push origin main --tags
```

---

## 5. Conflict Prevention & Synchronisation Rules

1. **`shared/types.py` is Immutable**: If an AI agent discovers a missing field, it must be coordinated as an additive optional field (`Optional[T] = None`) with all developers before modifying `develop`.
2. **Dedicated `requirements.txt`**: Each service has its own requirements file (`sidecar/requirements.txt`, `node/requirements.txt`, etc.). Never create a conflicting root-level requirements file.
3. **Container Boundary**: Services only interact over standard HTTP APIs across network boundaries using the schemas defined in `shared/types.py`.
