# Dev 1 ZK/ML Core — implementation and integration status

## Implemented

- `compile.py`: attempts EZKL ONNX compilation/setup first; creates explicitly labelled `mock-not-zk` development artifacts if EZKL or the model artifact is unavailable and fallback is enabled.
- `prove.py` / `verify_local.py`: enforce the canonical `shared.types.FEATURE_ORDER`, compute the shared input commitment, create the shared `ProofPayload`, and support a locally trusted Ed25519-signed test attestation. The mock verifier rejects altered public inputs, altered signatures, and attacker-supplied verification keys.
- `sidecar/`: FastAPI `/healthz`, `/metrics`, `POST /v1/prove` (202), `GET /v1/jobs/{job_id}`, durable SQLite jobs/outbox, duplicate decision handling, exponential retry, notice-before-proof delivery, idempotency keys, interrupted-job recovery, and minimisation of raw features/application IDs after intake/proving.
- `policy/sign.py`: canonical policy bytes, independent Ed25519 signatures, policy-hash verification, and a checked-in dual-signed **demo-only** policy.
- Tests cover the honest local mock flow, public-input tampering, forged mock signer, feature schema mismatch, policy mutation, API validation/idempotency, outbox retry/order, and privacy minimisation.

## Important limits — do not overclaim in the demo

1. The current environment does not have EZKL installed, and `model/models/scorecard.onnx` is not present. The checked-in policy and generated circuit descriptor therefore identify a **demo-only mock circuit/model**, not a production credit model.
2. The mock attestation is an Ed25519-signed development statement. It is **not Halo2, not zero knowledge, and not proof that inference was executed correctly**. It exists to test interfaces and tamper handling while native proving is unavailable.
3. A plain EZKL proof over the ONNX inference graph does not automatically bind the policy hash, salted model commitment `C`, input commitment `X`, decision bit, and threshold to the same proof. The native path intentionally refuses to treat an inference-only circuit as full policy-conformance proof until those values are constrained as public inputs in the compiled circuit.
4. `policy/example_policy.json` is self-contained and verifies cryptographically, but its public keys are included in the document and the signing keys are local demo keys. Production must pin/provision lender and LSP public keys out-of-band; the current sample is not an institutional identity trust anchor.
5. The repository's current Compose file uses internal HTTP for the LSP-to-lender hop. Set `SAKSHI_SIDECAR_REQUIRE_HTTPS=true` once TLS is configured; do not describe the present Compose traffic as HTTPS/mTLS.
6. The current development environment is Python 3.14.8; the sidecar Dockerfile pins Python 3.11 to align with the pinned EZKL dependency. Docker is unavailable in the current terminal, so an image build was not run here.

## Integration contract

- Shared payloads and feature order are imported from `shared.types`; that file was not modified.
- Sidecar APIs: `GET /healthz`, `GET /metrics`, `POST /v1/prove`, `GET /v1/jobs/{job_id}`.
- Outbound requests use `X-Sakshi-Key` and a stable `Idempotency-Key`; `DecisionNotice` is delivered before `ProofPayload`.
- Demo fallback can be disabled with `SAKSHI_SIDECAR_ALLOW_MOCK_PROOFS=false`; compilation fallback can be disabled with `SAKSHI_ALLOW_MOCK_PROOFS=false`. With fallback disabled, missing native full-statement proving fails closed.

## Verification run

From repository root:

```bash
python -m pytest tests/test_circuit.py -v
python -m pytest -q
python -m compileall -q circuits sidecar policy tests
```

Last run: **17 tests passed**. Existing deprecation warnings originate in the read-only `shared/types.py` contract (`Field(example=...)` and `datetime.utcnow()`); that shared file was intentionally not edited.
