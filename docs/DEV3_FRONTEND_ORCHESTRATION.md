# DEV 3: Frontend, Customer Demo & System Orchestration Spec

## 1. Role & Ownership
Dev 3 owns the end-to-end user experience (both customer and lender), the mock bank loan management system, and system integration:
1. **Customer Demo Side (Borrower Digital Lending Journey)**: The mobile/web digital lending application (DLA) where an applicant submits a loan request, consents to bureau pull, receives an instant provisional offer, and views an immutable **Cryptographic Decision Receipt**.
2. **Lender Operations & Risk Portal**: The NBFC/Bank institutional risk dashboard displaying real-time decision throughput, verification status badges, proof latency metrics, tamper experiment controls, and an immutable audit ledger.
3. **Mock LMS (Loan Management System)**: The lender's core banking disbursal service enforcing the strict **Fail-Closed Rule** (`no valid proof, no disbursal`).
4. **2-Container Master Topology**: Orchestrating the system into **exactly two containers**:
   - `sakshi-lsp`: Underwriting scoring model + Prover Sidecar + SQLite outbox (Zone 1).
   - `sakshi-lender`: All-in-one Lender Appliance hosting the Lender Node API, Verifier Pipeline, Append-Only Ledger, Mock LMS, and serving the built React static frontends (Zone 3).
5. **Single-Pass Integration Scripts**: Automated seeding (`scripts/demo_seed.py`) and one-click test runners (`scripts/run_full_demo.py`).

---

## 2. Frontend Design System: Institutional Indian Digital Banking (Zero AI Slop)

> ⚠️ **MANDATORY DESIGN RULE: ZERO AI SLOP**  
> Absolutely NO generic purple neon gradients, floating glassmorphism blobs, cyberpunk dark modes, or vague cryptocurrency buzzwords.  
> The interface must look and feel like an authentic, high-trust Indian tier-1 banking application (such as **HDFC Bank SmartHub, ICICI iMobile, Axis Open, Navi, or Cred**).

### 2.1 Color Palette
- **Primary Navy / Trust Base:** `#0A2540` / `#002D62` (Deep RBI/HDFC institutional navy).
- **Secondary Slate:** `#F4F6F8` (Crisp off-white background), `#E2E8F0` (Subtle 1px card borders).
- **Surface:** Pure `#FFFFFF` cards with crisp `shadow-sm` (no heavy blurry drop shadows).
- **Indian Banking Accent:** Deep Maroon/Crimson `#8B0000` or `#991B1B` for lender identity badges.
- **Verification Emerald (Success):** `#059669` (Solid, authoritative green).
- **Rejection / Violation (Alert):** `#DC2626` (Clear institutional error red).
- **Pending / SLA Clock (Amber):** `#D97706`.

### 2.2 Typography & Formatting
- **Font Stack:** Clean system sans (`Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto`).
- **Currency:** Must strictly use Indian Numbering Format with Rupee symbol (`₹1,50,000`, `₹25,00,000`, `₹300/mo`).
- **Tabular Data:** Hashes, commitments, and ledger sequences must use crisp monospace (`font-mono text-xs text-slate-600`).
- **Timestamps:** Real Indian Standard Time format (`20 Oct 2026, 20:15:32 IST`).
- **Regulatory Footers:** "Regulated Entity: NBFC-ICC Reg. No. N-07.XXXXX | In compliance with RBI (Digital Lending) Directions, 2025".

---

## 3. Frontend Architecture & Routes

A single React (Vite + Tailwind) application serving both personas via clean routing:

```
dashboard/
├── src/
│   ├── pages/
│   │   ├── BorrowerPortal.tsx     # Route: /borrower (Mobile-framed loan app)
│   │   ├── BorrowerReceipt.tsx    # Route: /receipt/:id (Cryptographic decision receipt)
│   │   ├── LenderDashboard.tsx    # Route: / or /lender (Institutional risk & audit portal)
│   │   ├── TamperDemo.tsx         # Route: /tamper (Live hackathon judge demo panel)
│   │   └── AuditLedger.tsx        # Route: /ledger (Full cryptographic hash chain inspector)
│   ├── components/
│   │   ├── borrower/
│   │   │   ├── LoanSlider.tsx     # Amount (₹50k - ₹5L) and tenure selector
│   │   │   ├── ApplicantForm.tsx  # PAN, Income, Bureau consent toggle
│   │   │   ├── DisbursalWait.tsx  # "Verifying conformance with Lender policy..."
│   │   │   └── DisbursalSuccess.tsx # "Funds credited to Bank Account"
│   │   ├── lender/
│   │   │   ├── StatsOverview.tsx  # Verified / Failed / SLA breaches counters
│   │   │   ├── LiveDecisionFeed.tsx # Real-time polling decision log with reason badges
│   │   │   ├── ProofInspectorModal.tsx # Shows C, X, Policy Hash, VK, Proof Bytes
│   │   │   └── HashChainBadge.tsx # "Ledger Integrity: Cryptographically Verified"
│   │   └── tamper/
│   │       └── TamperConsole.tsx  # The 5 one-click attack simulation triggers
```

---

## 4. Customer Demo Experience (Borrower DLA Screen)

### 4.1 Screen 1: Instant Loan Application (`/borrower`)
- Displays an authentic mobile-styled preview container on desktop (or responsive full-screen).
- **Borrower Inputs:**
  - Name: Priya Sharma
  - Requested Amount Slider: `₹1,50,000` (Tenure: 24 Months, EMI: `₹7,215/mo`).
  - Monthly Income: `₹75,000`.
  - Self-declared FOIR: `35%`.
  - Checkbox: "I consent to fetch CIBIL score & Account Aggregator statement under DPDP Act 2025".
- CTA Button: `[Check Eligibility & Apply]`.

### 4.2 Screen 2: Underwriting & Asynchronous Proving
- When the applicant clicks Apply:
  1. The DLA calls `POST http://localhost:8000/v1/demo/apply`.
  2. The applicant immediately sees: **"Provisional Sanction Approved! Preparing Bank Disbursal..."** (Borrower UX is never blocked by proving).
  3. A progress indicator shows:
     - `✓ Identity & PAN Verification (UIDAI/NSDL)`
     - `✓ Bureau Score Fetched (CIBIL: 742)`
     - `⏳ Generating Zero-Knowledge Conformance Proof (EZKL Halo2)...`
     - `⏳ Verifier Disbursal Gate Check...`
  4. The Mock LMS calls `GET /v1/decisions/{decision_id}/status`.
  5. Once the proof arrives and verifies (2–4 seconds):
     - Screen updates to: **"Loan Disbursed! ₹1,50,000 sent to HDFC Bank A/C ending 4821"**.
     - Provides button: `[View Cryptographic Decision Receipt]`.

### 4.3 Screen 3: Cryptographic Decision Receipt (`/receipt/:id`)
- A formal, bank-grade certificate that the borrower can save or print:
  - **Decision:** SANCTIONED & VERIFIED
  - **Policy Reference:** `pol_nbfc42_lspX_personal_v1`
  - **Model Commitment ($C$):** `0x9f3ca82e...` (Verified approved model)
  - **Input Commitment ($X$):** `0x7d0211bc...` (Cryptographically bound features)
  - **Ledger Sequence:** `#1042` (Permanently anchored in append-only audit trail)
  - **RBI Disclaimer:** "This decision was executed under an algorithm verified for strict conformance with NBFC Board-Approved Policy without third-party data exposure."

---

## 5. Mock LMS Disbursal Gate (`mock_lms/`)

Implements the **Fail-Closed Disbursal Rule**:

```python
# mock_lms/disbursal_gate.py
import httpx
from pydantic import BaseModel

class DisbursalResult(BaseModel):
    decision_id: str
    disbursed: bool
    status: str
    failure_reason: str | None = None
    disbursal_reference: str | None = None

async def attempt_loan_disbursal(lender_node_url: str, decision_id: str, amount: float) -> DisbursalResult:
    """
    FAIL-CLOSED GATE RULE:
    Funds move from lender directly to the borrower's bank account ONLY IF
    the decision status is strictly VERIFIED.
    If the node is unreachable, the proof is missing, or status is FAILED,
    disbursal is immediately held.
    """
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(f"{lender_node_url}/v1/decisions/{decision_id}/status")
    except Exception as exc:
        return DisbursalResult(
            decision_id=decision_id,
            disbursed=False,
            status="GATE_OFFLINE",
            failure_reason="Fail-closed: Lender Verifier Node unreachable. Funds held."
        )

    if resp.status_code != 200:
        return DisbursalResult(
            decision_id=decision_id,
            disbursed=False,
            status="NOT_FOUND",
            failure_reason="No decision notice recorded."
        )

    data = resp.json()
    status = data.get("status")

    if status == "VERIFIED":
        return DisbursalResult(
            decision_id=decision_id,
            disbursed=True,
            status="VERIFIED",
            disbursal_reference=f"NEFT-RB-{decision_id}-SUCCESS"
        )
    elif status == "NOTICE_RECEIVED":
        return DisbursalResult(
            decision_id=decision_id,
            disbursed=False,
            status="PENDING_PROOF",
            failure_reason="Awaiting zero-knowledge proof verification. Disbursal queued."
        )
    else:
        # FAILED, EXPIRED, or TAMPERED
        return DisbursalResult(
            decision_id=decision_id,
            disbursed=False,
            status=status,
            failure_reason=f"Disbursal blocked by gate: {data.get('failure_reason')}"
        )
```

---

## 6. Strict 2-Container Topology

Instead of proliferating small micro-containers, the entire platform runs in **strictly two containers**:

1. **`sakshi-lsp` (Container 1 - Portless / Isolated in `lsp_net`):**
   - Underwriting scoring engine.
   - EZKL witness builder & proving worker.
   - SQLite outbox & outbound HTTPS client uploading to `http://sakshi-lender:8000`.
2. **`sakshi-lender` (Container 2 - Port 8000 on `lender_net`):**
   - Lender Node FastAPI application.
   - Verifier pipeline (V1 to V9).
   - Append-only hash chain ledger.
   - Mock LMS loan router.
   - Built React frontend served as static assets directly by FastAPI (`StaticFiles(directory="dashboard/dist")`).

---

## 7. Testing Requirements & Verification

Dev 3 must ensure the following tests pass on the branch before merge:
- `tests/test_mock_lms.py`: Tests that the disbursal gate allows disbursal for `VERIFIED` and rejects for `NOTICE_RECEIVED`, `FAILED`, and network timeouts.
- `tests/test_demo_flows.py`: Tests that honest and tamper demo endpoints produce expected state transitions.
- Frontend build test: `cd dashboard && npm run build` completes with zero TypeScript or lint errors.
