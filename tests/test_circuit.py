from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

import pytest

from circuits.compile import compile_circuit
from circuits.prove import generate_zk_proof
from circuits.verify_local import verify_local, verify_mock_signature_only
from policy.sign import generate_signed_policy, verify_policy
from shared.types import FEATURE_ORDER, compute_input_hash


FEATURES = {
    "bureau_score": 750.0,
    "monthly_income": 80000.0,
    "foir": 0.30,
    "loan_tenure_months": 36.0,
    "num_active_loans": 1.0,
    "num_enquiries_6m": 0.0,
    "bank_account_age_months": 60.0,
    "loan_amount_requested": 100000.0,
    "behaviour_idx": 0.20,
    "employment_type": 0.0,
}


def test_circuit_compilation_and_proving(tmp_path, monkeypatch):
    # This environment has no EZKL installation; force the documented, labelled fallback.
    monkeypatch.setenv("SAKSHI_ALLOW_MOCK_PROOFS", "true")
    circuit_hash = compile_circuit(allow_mock=True, force_mock=True)
    assert len(circuit_hash) == 64

    commitment = "0x" + hashlib.sha256(b"test-model-commitment").hexdigest()
    policy = generate_signed_policy(
        commitment, circuit_hash,
        policy_path=tmp_path / "policy.json",
        lsp_private_key_path=tmp_path / "lsp.pem",
        lender_private_key_path=tmp_path / "lender.pem",
        persist=True,
    )
    assert len(policy["policy_hash"]) == 64
    assert verify_policy(policy)

    payload = generate_zk_proof(
        decision_id="d_test_101", policy_id=policy["policy_id"], features=FEATURES,
        decision=1, policy_hash=policy["policy_hash"], model_commitment=commitment, threshold=0.200,
    )
    assert payload.decision_id == "d_test_101"
    assert payload.public_inputs.C == commitment
    assert payload.public_inputs.X == compute_input_hash(FEATURES)
    assert list(FEATURES.keys()) != []
    assert len(base64.b64decode(payload.proof)) > 50
    assert verify_local(payload, allow_mock=True)
    decoded = json.loads(base64.b64decode(payload.proof))
    assert decoded["format"] == "SAKSHI_MOCK_ATTESTATION_NOT_ZK_V1"
    assert verify_local(payload, allow_mock=False) is False


def test_tamper_model_commitment_fails():
    payload = generate_zk_proof("d_model", "pol_test", FEATURES, 1, "policy-hash", "model-C", 0.2)
    changed = payload.model_copy(deep=True)
    changed.public_inputs.C = "attacker-model-C"
    assert verify_local(payload, allow_mock=True)
    assert not verify_local(changed, allow_mock=True)


def test_tamper_threshold_fails():
    payload = generate_zk_proof("d_threshold", "pol_test", FEATURES, 1, "policy-hash", "model-C", 0.2)
    changed = payload.model_copy(deep=True)
    changed.public_inputs.threshold = 0.05
    assert not verify_local(changed, allow_mock=True)


def test_tamper_proof_bytes_fails():
    payload = generate_zk_proof("d_bytes", "pol_test", FEATURES, 1, "policy-hash", "model-C", 0.2)
    envelope = json.loads(base64.b64decode(payload.proof))
    signature = bytearray(base64.b64decode(envelope["signature_b64"]))
    signature[0] ^= 0x01
    envelope["signature_b64"] = base64.b64encode(signature).decode()
    payload.proof = base64.b64encode(json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()).decode()
    assert not verify_local(payload, allow_mock=True)
    assert not verify_mock_signature_only(payload.proof)


def test_feature_schema_must_match_shared_order():
    payload = dict(FEATURES)
    payload.pop(FEATURE_ORDER[0])
    with pytest.raises(ValueError, match="feature schema mismatch"):
        generate_zk_proof("d_missing", "pol_test", payload, 1, "policy-hash", "model-C")


def test_dual_signed_policy_rejects_mutation(tmp_path):
    policy = generate_signed_policy(
        "model-C", "circuit-H", policy_path=tmp_path / "policy.json",
        lsp_private_key_path=tmp_path / "lsp.pem", lender_private_key_path=tmp_path / "lender.pem",
    )
    assert verify_policy(policy)
    policy["decision_threshold"] = 0.05
    assert not verify_policy(policy)


def test_mock_proof_cannot_choose_its_own_trust_key():
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    payload = generate_zk_proof("d_forged", "pol_test", FEATURES, 1, "policy-hash", "model-C", 0.2)
    envelope = json.loads(base64.b64decode(payload.proof))
    attacker = Ed25519PrivateKey.generate()
    statement = base64.b64decode(envelope["statement_b64"])
    envelope["signature_b64"] = base64.b64encode(attacker.sign(statement)).decode()
    envelope["verification_key_pem"] = attacker.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    payload.proof = base64.b64encode(json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()).decode()
    assert not verify_local(payload, allow_mock=True)
