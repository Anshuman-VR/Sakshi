# SAKSHI: Git Workflow, Collaborator Guide & Single-Pass Merge

This guide details the exact operational steps for the **Repository Owner** and the development team to build, test, merge, and containerize the project in a 24-hour sprint.

---

## 1. Action Checklist for Repo Owner (Hour 0)

As the repository owner, perform these steps on your machine right now:

### Step 1: Connect to your GitHub Remote
If you already have a GitHub repository created, link it:
```bash
# Add your GitHub remote (replace with your repo URL)
git remote add origin https://github.com/<YOUR_USERNAME_OR_ORG>/Sakshi.git

# Verify remote
git remote -v
```

### Step 2: Push Base Branches to GitHub
Push the initialized base commits and branches:
```bash
# 1. Push main
git push -u origin main --force

# 2. Push develop (contains frozen contracts in shared/types.py)
git push -u origin develop

# 3. Push the 3 developer feature branches
git push -u origin feature/branch-1-zkml-core
git push -u origin feature/branch-2-lender-node
git push -u origin feature/branch-3-frontend-demo
```

### Step 3: Add Your Teammates as Collaborators on GitHub
1. Open your repository on GitHub in your browser (`https://github.com/<YOUR_ORG>/Sakshi`).
2. Click **Settings** (top navigation).
3. Under the *Access* section in the left sidebar, click **Collaborators**.
4. Click the green button: **Add people**.
5. Enter each developer's GitHub username or email address and send the invitation.
6. Once they accept, they will have direct push access to their assigned branches.

### Step 4: Distribute Prompts to Developers
Send each developer their exact assigned markdown file (located in the repository):
- **Developer 1 (ZK/ML Lead):** Give them [`DEV1_ZKML_CORE.md`](file:///c:/Users/Abcom/Desktop/Work/Code%20Projects/Python/Sakshi/DEV1_ZKML_CORE.md) and instruct them to work exclusively on `feature/branch-1-zkml-core`.
- **Developer 2 (Lender Node Lead):** Give them [`DEV2_LENDER_NODE.md`](file:///c:/Users/Abcom/Desktop/Work/Code%20Projects/Python/Sakshi/DEV2_LENDER_NODE.md) and instruct them to work exclusively on `feature/branch-2-lender-node`.
- **Developer 3 (Frontend & DevOps Lead):** Give them [`DEV3_FRONTEND_ORCHESTRATION.md`](file:///c:/Users/Abcom/Desktop/Work/Code%20Projects/Python/Sakshi/DEV3_FRONTEND_ORCHESTRATION.md) and instruct them to work exclusively on `feature/branch-3-frontend-demo`.

---

## 2. Directory Ownership Matrix (Zero Merge Conflicts)

Because each developer owns an entirely disjoint directory tree, git merges will be 100% clean and deterministic:

| Directory | Owner Branch | Developer | Rules |
| :--- | :--- | :--- | :--- |
| `shared/` | `develop` | **All** | **FROZEN at Hour 2**. Zero edits without unanimous team agreement. |
| `model/` | `feature/branch-1-zkml-core` | Dev 1 | Dev 1 exclusive |
| `circuits/` | `feature/branch-1-zkml-core` | Dev 1 | Dev 1 exclusive |
| `sidecar/` | `feature/branch-1-zkml-core` | Dev 1 | Dev 1 exclusive |
| `policy/` | `feature/branch-1-zkml-core` | Dev 1 | Dev 1 exclusive |
| `node/` | `feature/branch-2-lender-node` | Dev 2 | Dev 2 exclusive |
| `adapter/` | `feature/branch-2-lender-node` | Dev 2 | Dev 2 exclusive |
| `dashboard/` | `feature/branch-3-frontend-demo` | Dev 3 | Dev 3 exclusive |
| `mock_lms/` | `feature/branch-3-frontend-demo` | Dev 3 | Dev 3 exclusive |
| `deploy/` | `feature/branch-3-frontend-demo` | Dev 3 | Dev 3 exclusive |
| `scripts/` | `feature/branch-3-frontend-demo` | Dev 3 | Dev 3 exclusive |

---

## 3. The "Merge Before Containerization" Workflow

> 💡 **CRITICAL HACKATHON RULE:**  
> **Never build or debug multi-container Docker images on isolated branches.**  
> Container building creates cache headaches and wastes precious hours.  
> Each developer builds and tests purely in native Python / Vite on their local branch. Containerization happens **only once, after the merge**.

```
[Branch 1 Native Tests]     [Branch 2 Native Tests]     [Branch 3 Native Tests]
(pytest test_circuit.py)    (pytest test_verifier.py)   (npm run build && test)
           │                           │                           │
           └───────────────────────────┼───────────────────────────┘
                                       │
                                       ▼
                       [Merge into release/v1.0-hackathon]
                                       │
                                       ▼
                        [Native Integration Smoke Test]
                                       │
                                       ▼
                  [Build the 2 Production Containers in deploy/]
                    ├── Container 1: sakshi-lsp
                    └── Container 2: sakshi-lender
                                       │
                                       ▼
                         [Push Final Merge to main]
```

---

## 4. Branch Testing Requirements (Before Merging)

### Dev 1 Local Verification Checklist (`branch-1`):
```bash
# 1. Test dataset generation and model training parity
python model/generate_data.py
python model/train.py
python model/parity_report.py  # Must assert >98% agreement between float and quantized

# 2. Test circuit compilation and local proof verification
python circuits/compile.py
python circuits/verify_local.py

# 3. Run unit tests
pytest tests/test_circuit.py tests/test_sidecar.py
```

### Dev 2 Local Verification Checklist (`branch-2`):
```bash
# 1. Run database initialization
python node/database.py

# 2. Run all verifier pipeline and ledger tests
pytest tests/test_verifier.py tests/test_ledger.py tests/test_gate_route.py
# All 9 tamper and integrity assertions MUST pass
```

### Dev 3 Local Verification Checklist (`branch-3`):
```bash
# 1. Test frontend build
cd dashboard
npm install
npm run build  # Must complete with zero errors into dashboard/dist

# 2. Test mock LMS gate
cd ..
pytest tests/test_mock_lms.py
```

---

## 5. Single-Pass Merge Procedure (Hour 21–22)

Once all three developers have completed Stage 5 and their local tests pass:

```bash
# 1. Fetch latest changes from all remotes
git fetch --all

# 2. Switch to develop and update
git checkout develop
git pull origin develop

# 3. Create integration release branch
git checkout -b release/v1.0-hackathon

# 4. Merge Branch 1 (ZK/ML Core)
git merge --no-ff origin/feature/branch-1-zkml-core -m "merge: ZK/ML Core pipeline (Branch 1)"

# 5. Merge Branch 2 (Lender Node)
git merge --no-ff origin/feature/branch-2-lender-node -m "merge: Lender Node & Verifier Engine (Branch 2)"

# 6. Merge Branch 3 (Frontend & Orchestration)
git merge --no-ff origin/feature/branch-3-frontend-demo -m "merge: Frontend & Mock LMS (Branch 3)"
```

---

## 6. Containerization & Live Rehearsal (Hour 22–24)

Now that all code is unified in `release/v1.0-hackathon`:

```bash
# 1. Build the strictly 2 containers
docker compose -f deploy/docker-compose.yml build

# 2. Start the 2-container topology
docker compose -f deploy/docker-compose.yml up -d

# 3. Check health of both containers
docker compose -f deploy/docker-compose.yml ps

# 4. Seed the demo environment (Registers approved model & policy)
python scripts/demo_seed.py

# 5. Run full automated demo rehearsal
python scripts/run_full_demo.py

# 6. Open the frontends in browser:
# - Lender Risk & Operations Portal: http://localhost:8000/
# - Borrower Loan Journey (Mobile view): http://localhost:8000/borrower
```

---

## 7. Promote to Main & Final Tag

```bash
git checkout main
git merge --no-ff release/v1.0-hackathon -m "release: Sakshi v1.0.0 complete 24h hackathon build"
git tag -a v1.0.0-hackathon -m "Sakshi 24h Hackathon Final Working Release"
git push origin main --tags
```
