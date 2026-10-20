# Dev 3 integration contract

This note records the API and file ownership decisions used by the Dev 3 frontend. It is intended to reduce merge conflicts when the other workstreams land.

## UI modes are deliberately isolated

- `/`, `/lender`, `/borrower`, `/receipt/:id`, and `/ledger` are the live application surfaces. They read live API data or clearly show that integration is unavailable.
- `/demo` is a separate client-only simulation. It uses local fixtures and browser state; it must not POST fabricated proof payloads to `/v1/proofs`, create lender decisions, seed the ledger, or call a disbursal endpoint.
- The documented `/v1/demo/apply` endpoint in `DEV2_PROMPT.md` currently writes a `VERIFIED` decision directly. The live borrower page intentionally does **not** call it because it is a simulation shortcut, not a safe production application contract.
- A real borrower submission contract is not defined in `shared/types.py` or the checked-in backend source. Do not invent a public endpoint for raw borrower features. Agree with Dev 1 and Dev 2 on a privacy-safe application path before enabling live submission.

## Contracts consumed by the frontend

- `GET /healthz` — API availability indicator.
- `GET /v1/dashboard/summary` — `shared.types.DashboardSummary`, including `total_decisions`, `verified`, `failed`, `pending`, `expired`, `recent_decisions`, latency percentiles, `ledger_seq`, and `chain_valid`.
- `GET /v1/decisions/{decision_id}/status` — `shared.types.DecisionStatusResponse`. A receipt displays returned status only; it never assumes success.
- `GET /v1/dashboard/ledger?limit=50` — described in `DEV2_LENDER_NODE.md`; frontend accepts a list or an object with `entries`/`items`. Align the exact response envelope with Dev 2 before merge.
- Proof submissions follow `shared.types.ProofPayload`: `decision_id`, `policy_id`, base64 `proof`, and `public_inputs` with `policy_hash`, `C`, `X`, `decision`, `threshold`, `epoch`. Only the isolated demo fixtures currently use the failure labels from `shared.types.FailureReason`.
- Borrower model features follow `shared.types.FEATURE_ORDER`; the browser must not send raw feature vectors to the lender verifier. The current public API contract does not specify a secure browser-to-LSP application endpoint.

## Ownership to avoid overlapping edits

- Dev 3 owns `dashboard/` (including the final `BorrowerPortal.tsx` UI), `mock_lms/`, `scripts/demo_seed.py`, `scripts/run_full_demo.py`, `tests/test_mock_lms.py`, `deploy/docker-compose.yml`, and the integration Dockerfiles `node/Dockerfile` and `sidecar/Dockerfile`.
- Dev 2 owns `node/main.py`, backend modules, and `node/requirements.txt`. Dev 1 owns sidecar application modules and `sidecar/requirements.txt`. Dev 4 should provide model/persona schemas and sample features to Dev 3 rather than independently adding `dashboard/src/pages/BorrowerPortal.tsx`; its prompt currently overlaps that UI file. Avoid modifying these app/dependency files from Dev 3 unless coordinated.
- `shared/types.py` is a shared read-only contract. Dev 3 has not modified it.
- Dockerfiles are integration-owned by Dev 3 because they assemble the services and React static assets. Dev 2 must mount `dashboard/dist` as FastAPI static assets and keep `/v1/*` API routes working alongside the SPA fallback. Other developers should communicate required Dockerfile changes rather than independently replacing them. Docker bridge networks do not enforce one-way traffic; production deployments need separate egress controls if strict outbound-only LSP traffic is required.

## Design and safety rules

- Neo-brutalist styling is intentionally restrained: warm paper background, strong ink outlines, offset shadows, Space Grotesk/mono labels, and lime/coral/lavender accents. Responsive layout, keyboard focus, and reduced-motion support are included.
- All monetary UI uses `Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' })`.
- Dates from APIs are formatted in `Asia/Kolkata` and labelled IST.
- UI indicators are never a security boundary. The Mock LMS gate makes the allow/deny decision server-side and allows only exact `VERIFIED`; all other states fail closed.
