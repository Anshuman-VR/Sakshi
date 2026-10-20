# Dev 1 Completion Report — ZKML Core

**Project:** Sakshi  
**Branch:** `feature/branch-1-zkml-core`  
**Latest confirmed commit:** `4f30192` — `feat: finalize EZKL inference proof integration`  
**Owner:** Dev 1 — ZKML Core  
**Status:** Core native inference-proof implementation completed; full policy-conformance proof and cross-component integration remain incomplete.

---

## 1. Executive Summary

Dev 1 implemented the core model-inference and zero-knowledge proof pipeline using EZKL and Halo2. The implementation replaces reliance on a mock-only proof path with a native EZKL compilation, setup, proof-generation, and verification workflow.

The trained logistic-regression scorecard is exported to an EZKL-compatible ONNX graph. The prover can generate a native proof for model inference, and the local verifier validates the proof and performs additional application-level checks involving the model commitment, policy configuration, policy signatures, probability threshold, and decision consistency.

A previous model-development environment completed the regression suite with **18 passing tests**. A separate native EZKL smoke test successfully generated and verified a real proof.

These results establish a functional foundation for Sakshi's ZKML component. They do **not** establish that every lending-policy requirement is enforced inside one cryptographically bound zero-knowledge statement.

The remaining work is to integrate this component with Dev 2's lender node and Dev 3's frontend/orchestration, agree on the complete proof statement and data contracts, and validate the end-to-end system.

## 2. Delivered Implementation

### 2.1 Model export and inference

**Files:**
- `model/export_onnx.py`
- `model/models/scorecard.onnx`
- `model/models/scorecard.pkl`
- `model/parity_report.py`
- `model/parity_report.json`
- `model/requirements.txt`

The export path represents the trained binary logistic-regression scorecard using the EZKL-compatible ONNX operations `MatMul`, `Add`, and `Sigmoid`.

The exporter validates the expected binary-classifier structure and generates the inference graph used by the proof pipeline.

The serialized scikit-learn model remains available as `scorecard.pkl`, while the ONNX model is the inference artifact consumed by EZKL.

The parity report compares scikit-learn float32 probabilities with ONNX Runtime float32 probabilities. The recorded report covers 1,000 evaluated records and reports 100% decision agreement at threshold 0.20, with a maximum probability delta of approximately `3.3e-07`.

**Interpretation:** This is evidence of agreement between the reference model and ONNX Runtime for the reported sample. It is not a measurement of EZKL quantization error or proof-circuit parity.

### 2.2 Native EZKL compilation and setup

**File:** `circuits/compile.py`

The compilation pipeline was updated to use native EZKL compilation and setup rather than treating a mock proof as equivalent to a real ZK proof.

The native workflow generates the circuit and the associated proving and verification material, including settings and SRS artifacts.

The development integration uses EZKL version `23.0.5`. The corresponding dependency is pinned in `sidecar/requirements.txt`.

The compilation code also distinguishes the development/mock path from the native proof path and records metadata describing the backend and its supported statement.

**Artifact note:** Generated artifacts under `circuits/artifacts/` are ignored by Git because of their size. They were generated locally during development, but are not included in the source commit. A new environment must provision the required dependencies and regenerate or securely retrieve the artifacts using a reproducible setup process.

### 2.3 Proof generation

**File:** `circuits/prove.py`

The prover integration was updated to support native EZKL proof generation.

The native path checks for the required compiled artifacts, settings, SRS, and model metadata. It generates a witness and proof using EZKL and reads the model probability from the witness output.

The implementation checks decision consistency against the probability represented by the circuit's quantized computation. It also rejects relevant mismatches, including incompatible model commitments and inconsistent claimed decisions.

The proof-generation code uses temporary files for intermediate inputs, witnesses, and proof material.

A development/mock proof path remains available. That path uses an Ed25519 development attestation and must not be represented as a zero-knowledge proof.

### 2.4 Local verification

**File:** `circuits/verify_local.py`

The verifier was updated to verify native EZKL proofs and perform additional application-level validation.

The validation includes:
- Native proof verification using the expected verification material.
- Validation of the expected backend and statement metadata.
- Model-commitment consistency checks.
- Loading the trusted local example policy.
- Policy signature and policy-hash validation.
- Policy identifier, model commitment, threshold, and circuit-hash consistency checks.
- Input-commitment format checks.
- Consistency between the public model probability, configured threshold, and claimed decision.

These application checks are important, but they must not be confused with constraints enforced by the zero-knowledge circuit itself. A check performed by the local verifier is not automatically a cryptographic proof that the underlying private data satisfies that condition.

### 2.5 Policy configuration

**File:** `policy/example_policy.json`

The example policy was updated to contain the relevant model and circuit metadata and development signatures.

The example policy's signatures and metadata were checked successfully during the earlier integration work.

**Trust limitation:** The current policy uses development/demo keys. The policy file and its embedded public keys are not a production institutional trust root. Production deployment requires an explicit, independently provisioned trust model for lender and LSP signing keys, including key rotation and revocation procedures.

### 2.6 Regression tests and dependencies

**Files:**
- `tests/test_circuit.py`
- `tests/test_model.py`
- `sidecar/requirements.txt`
- `model/requirements.txt`

The tests were adjusted to distinguish explicit mock tests from native compilation and to reflect the updated ONNX graph and parity-report fields.

The model-development environment previously completed the existing suite with **18 passing tests** after the changes.

A later attempt to rerun the tests in the active system Python environment failed during test collection because scikit-learn was unavailable there. An environment rebuild was attempted but not completed.

Consequently, the accurate test status is:

- Historical regression run: 18 tests passed in the model-development environment.
- Historical native EZKL smoke test: proof generation and verification succeeded.
- Fresh test run in the active system environment: not completed successfully because dependencies were missing.
- Docker image build and full deployment verification: not confirmed.

No claim should be made that the latest commit has been validated by a fresh, clean-environment test run.

## 3. Confirmed Proof Guarantees and Limitations

### 3.1 What the current implementation demonstrates

The native EZKL smoke test successfully:
1. Used a sample from the available LendingClub-derived dataset.
2. Generated a native EZKL proof for the model-inference computation.
3. Verified the resulting proof successfully.
4. Checked the model probability against the configured decision threshold.
5. Rejected tested changes to the threshold or model commitment in the application verification flow.

The demonstrated circuit statement is fundamentally **model inference with a public probability output and private input**.

### 3.2 What is not yet proven as one complete statement

The current implementation does not establish that all of the following are simultaneously constrained and cryptographically bound in one proof:

- The exact policy hash.
- The feature/input commitment `X`.
- The model commitment `C`.
- The policy threshold.
- The final decision.
- The epoch or other freshness/replay-related metadata.
- Any additional hard lending-policy rules.

Some of these values are checked by the local verifier or application logic. Those checks are useful, but they do not substitute for a circuit or reviewed cryptographic construction that binds all required values together.

Until the statement is completed and reviewed, Sakshi must not claim that the current proof proves full policy conformance, lender-rule compliance, or correctness of every decision-making stage.

### 3.3 Mock-proof distinction

The mock proof path is a development mechanism. Its Ed25519 attestation is not equivalent to an EZKL/Halo2 zero-knowledge proof.

Production or integration configurations must explicitly identify whether the native or mock backend is being used and must not silently accept a mock proof where a native proof is required.

## 4. Remaining Work for Dev 1

### P0 — Define and complete the cryptographic statement

Coordinate with the master agent before changing shared contracts.

Agree on the exact statement that the proof must establish, including:
- What `C` commits to: the serialized model, ONNX model, compiled circuit, model parameters, or a precisely defined combination.
- How `X` is computed, who computes it, and how its relationship to the actual private features is established.
- Which values are public inputs, private witnesses, or verifier-side trusted configuration.
- How the threshold and final decision are bound to the circuit's probability output.
- How policy identity, epoch, and replay protection are enforced.
- Which hard policy rules must be represented in the circuit and which may be checked outside it.

Implement and review the required public inputs, constraints, and/or a formally specified verifier construction. Test adversarial cases where each bound value is altered independently.

### P0 — Confirm preprocessing and feature consistency

Document and verify the complete path from lender-supplied application features to model input.

Ensure the preprocessing, feature ordering, missing-value handling, normalization, data types, and model version used by the lender node match those used by the training/export pipeline.

A proof of inference over an input vector does not prove that the vector was correctly derived from the original loan application. That relationship must be defined and validated as part of the end-to-end design.

### P1 — Reproducible native build

Document the exact supported Python, EZKL, ONNX, and ONNX Runtime versions and provide a reproducible setup/compile procedure.

Ensure the generated circuit metadata is tied to the correct ONNX artifact and settings. Determine which artifacts should be regenerated during deployment and which, if any, may be distributed through an authenticated artifact pipeline.

Do not commit very large proving keys or SRS files without an explicit repository decision.

### P1 — Fresh verification

Run the model and circuit regression tests in the intended pinned environment, followed by native proof-generation and verification tests. Confirm the deployed sidecar uses the native backend where required.

Exercise tampering, mismatched model/policy metadata, malformed commitments, threshold boundary cases, and invalid decisions.

### P1 — Update implementation documentation

Review `circuits/IMPLEMENTATION_STATUS.md`, which was previously known to contain stale statements about the EZKL implementation.

Update the documentation to distinguish:
- Native inference proof support.
- Application-level verifier checks.
- Mock-only development behavior.
- Remaining full-statement-binding work.

## 5. Integration Requirements for Dev 2 — Lender Node

Dev 2 owns the lender-side integration. The master agent should reconcile these requirements with `DEV2_LENDER_NODE.md`, `DEV2_PROMPT.md`, `DEV1_ZKML_CORE.md`, and the shared interface definitions.

1. **Input contract:** Confirm the exact schema, types, feature order, preprocessing, and validation rules for loan application data passed to the ZKML component.
2. **Model identity:** Agree on a stable model-version and commitment convention. The lender must not independently invent a commitment format.
3. **Proof request/response:** Confirm the request fields and response schema for inference, proof generation, verification, and errors. Use the shared types as the source of truth.
4. **Policy handling:** Define which policy configuration the lender trusts and how policy identifiers, hashes, signatures, and threshold versions are checked.
5. **Decision semantics:** Define precisely how probability, threshold, decision, and boundary values are interpreted across Dev 1 and Dev 2.
6. **Failure handling:** Reject invalid proofs, unexpected model identities, stale epochs, malformed commitments, and unavailable native proof infrastructure where the policy requires a valid proof.
7. **Security boundary:** Clearly distinguish a valid proof of model inference from a claim that the loan application itself is truthful or that all lending policy rules have been satisfied.
8. **Transport security:** The current integration was not confirmed to have production TLS/mTLS. Internal HTTP must not be treated as production-secure transport merely because the sidecar has a configuration flag that can require HTTPS.

Dev 1 and Dev 2 must agree on the contract before either side independently changes shared schemas.

## 6. Integration Requirements for Dev 3 — Frontend and Orchestration

Dev 3 owns frontend/orchestration integration. The master agent should reconcile these items with `DEV3_FRONTEND_ORCHESTRATION.md` and the current shared types.

1. Confirm how the frontend starts a loan assessment and obtains the final lender response.
2. Ensure loading, success, rejection, proof failure, policy mismatch, and service-unavailable states are represented distinctly.
3. Display only decision information and proof-verification status actually returned and validated by the backend.
4. Do not display a generic “policy verified” or “fully compliant” claim solely because model inference proof verification succeeded.
5. Keep the frontend aligned with the shared request/response types and error contract.
6. Confirm that the frontend cannot supply or override trusted model commitments, policy trust roots, or verifier configuration.
7. Define whether and how proof metadata is exposed for auditability without exposing private application features.
8. Test the full frontend-to-lender-to-ZKML-to-verifier path, including failures and retries.

## 7. Master Agent Coordination Checklist

The master agent should use this report together with the Dev 2 and Dev 3 completion reports.

### Contract and architecture
- [ ] Reconcile Dev 1's proof schema with Dev 2's lender interface.
- [ ] Reconcile lender responses with Dev 3's frontend/orchestration contract.
- [ ] Treat shared types as the canonical interface; avoid unilateral schema changes.
- [ ] Decide and document the complete cryptographic statement and trust assumptions.
- [ ] Resolve model, circuit, policy, feature commitment, threshold, decision, and epoch semantics.

### Integration and security
- [ ] Confirm native proof generation and verification are wired into the actual deployed path.
- [ ] Confirm production cannot accidentally accept mock proofs.
- [ ] Establish production key provisioning, verification trust roots, and rotation procedures.
- [ ] Define HTTPS/mTLS and service authentication requirements.
- [ ] Verify replay protection and epoch/freshness semantics.
- [ ] Ensure UI and API claims match what is cryptographically proven.

### Validation and release
- [ ] Re-run regression tests in the pinned environment.
- [ ] Run a fresh native proof-generation and verification test.
- [ ] Run integration tests across Dev 1, Dev 2, and Dev 3.
- [ ] Validate error paths, threshold boundaries, mismatched commitments, and tampering.
- [ ] Check Docker builds and deployment configuration.
- [ ] Confirm artifact generation/distribution is reproducible.
- [ ] Confirm each development branch is pushed and merged through the agreed workflow.
- [ ] Review documentation and remove stale claims.

## 8. Repository and Git Notes

The latest user-confirmed local commit is `4f30192`, with message:

`feat: finalize EZKL inference proof integration`

The user's terminal output confirmed that the commit was created and included 14 files, including the ONNX model and serialized scikit-learn model.

The commit output also contained a warning about being unable to unlink a Git maintenance lock because the file was busy. The commit itself succeeded. The subsequent push had not yet been confirmed in the information available for this report.

The master agent should verify the remote branch state before assuming the changes have been pushed or merged.

The generated EZKL artifacts under `circuits/artifacts/` are ignored and are not part of this commit. The LendingClub-derived local CSV is also ignored and is not part of the source commit.

## 9. Final Status

**Delivered:** Native EZKL model-inference proof-generation and verification path, EZKL-compatible ONNX export, parity reporting, application-level policy and commitment checks, dependency updates, and adjusted regression tests.

**Historically demonstrated:** 18 regression tests passed in the model-development environment, and a native EZKL proof was generated and verified successfully.

**Not yet demonstrated:** A fresh clean-environment run, verified Docker build, production deployment, and full end-to-end integration with Dev 2 and Dev 3.

**Critical unresolved security requirement:** The current circuit does not yet prove the entire lending-policy contract in one cryptographically bound statement.

**Recommended ownership:** Dev 1 completes the statement and model-input consistency work with master-agent approval; Dev 2 finalizes lender integration and trust boundaries; Dev 3 finalizes frontend/orchestration behavior; the master agent resolves shared contracts and coordinates full-system validation.
